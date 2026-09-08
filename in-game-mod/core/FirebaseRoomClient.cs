using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace BigWalkHideSeek.Core;

internal sealed class FirebaseRoomClient : IDisposable
{
    private const string ApiKey = "AIzaSyD6tKAmVz4RwNdKPpEP1APBTlOQMWGVwCQ";
    private const string DatabaseUrl = "https://big-walk-hide-seek-default-rtdb.firebaseio.com/";
    private const string RoomAlphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private const int RoomCodeLength = 6;

    private static readonly HttpClient Http = new HttpClient
    {
        Timeout = TimeSpan.FromSeconds(12)
    };

    private readonly object stateLock = new object();
    private readonly SemaphoreSlim authGate = new SemaphoreSlim(1, 1);
    private readonly SemaphoreSlim matchWriteGate = new SemaphoreSlim(1, 1);

    private string idToken = string.Empty;
    private string refreshToken = string.Empty;
    private string uid = string.Empty;
    private long tokenExpiresAtMs;
    private long serverTimeOffsetMs;
    private long nextPollAtMs;
    private long nextOffsetRefreshAtMs;

    private string roomCode = string.Empty;
    private string localRole = "seeker";
    private string displayName = "Player";
    private string status = "Offline · create or join a room.";
    private bool connected;
    private bool host;
    private RoomSnapshot snapshot;

    private int userBusy;
    private int polling;
    private bool disposed;

    public bool IsBusy => Volatile.Read(ref userBusy) != 0;

    public bool IsConnected
    {
        get { lock (stateLock) return connected; }
    }

    public bool IsHost
    {
        get { lock (stateLock) return host; }
    }

    public string RoomCode
    {
        get { lock (stateLock) return roomCode; }
    }

    public string LocalRole
    {
        get { lock (stateLock) return localRole; }
    }

    public string Status
    {
        get { lock (stateLock) return status; }
    }

    public RoomSnapshot Snapshot
    {
        get { lock (stateLock) return snapshot; }
    }

    public static string NormalizeCode(string value)
    {
        if (string.IsNullOrEmpty(value))
            return string.Empty;

        var builder = new StringBuilder(RoomCodeLength);
        foreach (char raw in value.ToUpperInvariant())
        {
            if (builder.Length >= RoomCodeLength)
                break;
            if ((raw >= 'A' && raw <= 'Z') || (raw >= '0' && raw <= '9'))
                builder.Append(raw);
        }
        return builder.ToString();
    }

    public static string SanitizeName(string value)
    {
        string cleaned = string.IsNullOrWhiteSpace(value) ? "Player" : value.Trim();
        while (cleaned.Contains("  ", StringComparison.Ordinal))
            cleaned = cleaned.Replace("  ", " ", StringComparison.Ordinal);
        if (cleaned.Length > 28)
            cleaned = cleaned.Substring(0, 28);
        return string.IsNullOrWhiteSpace(cleaned) ? "Player" : cleaned;
    }

    public void Tick()
    {
        if (disposed || !IsConnected || IsBusy)
            return;

        long now = UtcNowMs();
        if (now < Interlocked.Read(ref nextPollAtMs))
            return;

        Interlocked.Exchange(ref nextPollAtMs, now + 750L);
        if (Interlocked.CompareExchange(ref polling, 1, 0) != 0)
            return;

        _ = PollSafeAsync();
    }

    public bool BeginCreate(string requestedName, string role)
    {
        return BeginUserOperation(
            () => CreateRoomAsync(requestedName, role),
            "Creating room…");
    }

    public bool BeginJoin(string code, string requestedName, string role)
    {
        return BeginUserOperation(
            () => JoinRoomAsync(code, requestedName, role),
            "Joining room…");
    }

    public bool BeginLeave()
    {
        if (!IsConnected)
            return false;

        return BeginUserOperation(LeaveRoomAsync, "Leaving room…");
    }

    public bool BeginChangeRole(string role)
    {
        if (!IsConnected)
            return false;

        return BeginUserOperation(
            () => ChangeRoleAsync(role),
            "Updating role…");
    }

    public void BeginPushMatchState(bool running, float elapsedSeconds)
    {
        if (!IsConnected || !IsHost || disposed)
            return;

        _ = PushMatchStateSafeAsync(running, elapsedSeconds);
    }

    public double GetSyncedMatchSeconds()
    {
        RoomSnapshot current = Snapshot;
        if (current == null)
            return 0d;

        long elapsed = Math.Max(0L, current.MatchElapsedMs);
        if (current.MatchRunning && current.MatchStartedAtMs > 0L)
        {
            long now = UtcNowMs() + Interlocked.Read(ref serverTimeOffsetMs);
            elapsed += Math.Max(0L, now - current.MatchStartedAtMs);
        }

        return elapsed / 1000d;
    }

    private bool BeginUserOperation(Func<Task> operation, string busyStatus)
    {
        if (disposed || Interlocked.CompareExchange(ref userBusy, 1, 0) != 0)
            return false;

        SetStatus(busyStatus);
        _ = RunUserOperationAsync(operation);
        return true;
    }

    private async Task RunUserOperationAsync(Func<Task> operation)
    {
        try
        {
            await operation().ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            SetStatus($"Room error · {ShortError(ex.Message)}");
        }
        finally
        {
            Volatile.Write(ref userBusy, 0);
        }
    }

    private async Task CreateRoomAsync(string requestedName, string role)
    {
        string name = SanitizeName(requestedName);
        string normalizedRole = NormalizeRole(role);
        await EnsureAuthAsync().ConfigureAwait(false);
        await RefreshServerOffsetSafeAsync().ConfigureAwait(false);

        string code = string.Empty;
        for (int attempt = 0; attempt < 12; attempt++)
        {
            string candidate = RandomCode();
            JsonElement? meta = await GetDbJsonAsync($"rooms/{candidate}/meta").ConfigureAwait(false);
            if (!meta.HasValue)
            {
                code = candidate;
                break;
            }
        }

        if (string.IsNullOrEmpty(code))
            throw new InvalidOperationException("Couldn't reserve a room code. Try again.");

        string localUid = GetUid();
        object timestamp = ServerTimestamp();
        var room = new Dictionary<string, object>
        {
            ["meta"] = new Dictionary<string, object>
            {
                ["hostUid"] = localUid,
                ["createdAt"] = timestamp,
                ["updatedAt"] = ServerTimestamp(),
                ["schema"] = 1,
                ["nativeCore"] = "0.0.25"
            },
            ["members"] = new Dictionary<string, object>
            {
                [localUid] = MemberPayload(name, normalizedRole)
            },
            ["state"] = new Dictionary<string, object>
            {
                ["match"] = new Dictionary<string, object>
                {
                    ["running"] = false,
                    ["elapsedMs"] = 0L,
                    ["startedAt"] = null
                },
                ["game"] = new Dictionary<string, object>(),
                ["revision"] = 0,
                ["updatedAt"] = ServerTimestamp(),
                ["updatedBy"] = localUid
            }
        };

        await SendDbAsync(HttpMethod.Put, $"rooms/{code}", room).ConfigureAwait(false);

        lock (stateLock)
        {
            roomCode = code;
            localRole = normalizedRole;
            displayName = name;
            connected = true;
            host = true;
            snapshot = null;
        }

        await PollRoomAsync().ConfigureAwait(false);
        SetStatus($"Room {code} connected · you are host.");
    }

    private async Task JoinRoomAsync(string rawCode, string requestedName, string role)
    {
        string code = NormalizeCode(rawCode);
        if (code.Length != RoomCodeLength)
            throw new InvalidOperationException("Enter a 6-character room code.");

        string name = SanitizeName(requestedName);
        string normalizedRole = NormalizeRole(role);
        await EnsureAuthAsync().ConfigureAwait(false);
        await RefreshServerOffsetSafeAsync().ConfigureAwait(false);

        JsonElement? roomJson = await GetDbJsonAsync($"rooms/{code}").ConfigureAwait(false);
        if (!roomJson.HasValue)
            throw new InvalidOperationException("Room not found. Check the code and try again.");

        RoomSnapshot existing = ParseSnapshot(roomJson.Value);
        string localUid = GetUid();
        if (normalizedRole == "hider" && HasOtherHider(existing, localUid))
            throw new InvalidOperationException("This room already has a Hider. Join as Seeker instead.");

        await SendDbAsync(HttpMethod.Put, $"rooms/{code}/members/{localUid}", MemberPayload(name, normalizedRole)).ConfigureAwait(false);

        lock (stateLock)
        {
            roomCode = code;
            localRole = normalizedRole;
            displayName = name;
            connected = true;
            host = string.Equals(existing.HostUid, localUid, StringComparison.Ordinal);
            snapshot = existing;
        }

        await PollRoomAsync().ConfigureAwait(false);
        SetStatus($"Room {code} connected.");
    }

    private async Task LeaveRoomAsync()
    {
        string code;
        string localUid;
        bool wasHost;
        lock (stateLock)
        {
            code = roomCode;
            localUid = uid;
            wasHost = host;
        }

        if (!string.IsNullOrEmpty(code) && !string.IsNullOrEmpty(localUid))
        {
            if (wasHost)
                await SendDbAsync(HttpMethod.Delete, $"rooms/{code}", null).ConfigureAwait(false);
            else
                await SendDbAsync(HttpMethod.Delete, $"rooms/{code}/members/{localUid}", null).ConfigureAwait(false);
        }

        ClearRoomState("Offline · create or join a room.");
    }

    private async Task ChangeRoleAsync(string role)
    {
        string normalizedRole = NormalizeRole(role);
        RoomSnapshot current = Snapshot;
        string localUid = GetUid();
        string code = RoomCode;

        if (string.IsNullOrEmpty(code))
            return;

        if (normalizedRole == "hider" && HasOtherHider(current, localUid))
        {
            SetStatus("This room already has a Hider.");
            return;
        }

        var patch = new Dictionary<string, object>
        {
            ["role"] = normalizedRole,
            ["lastSeen"] = ServerTimestamp()
        };
        await SendDbAsync(HttpMethod.Patch, $"rooms/{code}/members/{localUid}", patch).ConfigureAwait(false);

        lock (stateLock)
            localRole = normalizedRole;

        await PollRoomAsync().ConfigureAwait(false);
        SetStatus($"Role changed to {(normalizedRole == "hider" ? "Hider" : "Seeker")}.");
    }

    private async Task PushMatchStateSafeAsync(bool running, float elapsedSeconds)
    {
        await matchWriteGate.WaitAsync().ConfigureAwait(false);
        try
        {
            if (!IsConnected || !IsHost || disposed)
                return;

            long elapsedMs = Math.Max(0L, (long)Math.Round(elapsedSeconds * 1000d));
            var patch = new Dictionary<string, object>
            {
                ["match"] = new Dictionary<string, object>
                {
                    ["running"] = running,
                    ["elapsedMs"] = elapsedMs,
                    ["startedAt"] = running ? ServerTimestamp() : null
                },
                ["updatedAt"] = ServerTimestamp(),
                ["updatedBy"] = GetUid()
            };

            await SendDbAsync(HttpMethod.Patch, $"rooms/{RoomCode}/state", patch).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            SetStatus($"Match sync retry needed · {ShortError(ex.Message)}");
        }
        finally
        {
            matchWriteGate.Release();
        }
    }

    private async Task PollSafeAsync()
    {
        try
        {
            await PollRoomAsync().ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            if (IsConnected)
                SetStatus($"Reconnecting… {ShortError(ex.Message)}");
        }
        finally
        {
            Volatile.Write(ref polling, 0);
        }
    }

    private async Task PollRoomAsync()
    {
        string code = RoomCode;
        if (string.IsNullOrEmpty(code))
            return;

        JsonElement? roomJson = await GetDbJsonAsync($"rooms/{code}").ConfigureAwait(false);
        if (!roomJson.HasValue)
        {
            ClearRoomState("Room closed by host.");
            return;
        }

        RoomSnapshot next = ParseSnapshot(roomJson.Value);
        string localUid = GetUid();
        RoomMemberSnapshot self = FindMember(next, localUid);
        if (self == null)
        {
            ClearRoomState("You are no longer in this room.");
            return;
        }

        lock (stateLock)
        {
            snapshot = next;
            host = string.Equals(next.HostUid, localUid, StringComparison.Ordinal);
            localRole = NormalizeRole(self.Role);
            displayName = self.Name;
            connected = true;
            if (status.StartsWith("Reconnecting", StringComparison.Ordinal))
                status = $"Room {code} connected.";
        }

        long now = UtcNowMs();
        if (now >= Interlocked.Read(ref nextOffsetRefreshAtMs))
        {
            Interlocked.Exchange(ref nextOffsetRefreshAtMs, now + 60000L);
            await RefreshServerOffsetSafeAsync().ConfigureAwait(false);
        }
    }

    private async Task RefreshServerOffsetSafeAsync()
    {
        try
        {
            JsonElement? offset = await GetDbJsonAsync(".info/serverTimeOffset").ConfigureAwait(false);
            if (offset.HasValue && offset.Value.ValueKind == JsonValueKind.Number && offset.Value.TryGetInt64(out long value))
                Interlocked.Exchange(ref serverTimeOffsetMs, value);
        }
        catch
        {
            // System clock is a good enough fallback until the next poll succeeds.
        }
    }

    private async Task EnsureAuthAsync()
    {
        await authGate.WaitAsync().ConfigureAwait(false);
        try
        {
            long now = UtcNowMs();
            if (!string.IsNullOrEmpty(idToken) && now < tokenExpiresAtMs - 120000L)
                return;

            if (!string.IsNullOrEmpty(refreshToken))
            {
                try
                {
                    await RefreshAuthTokenAsync().ConfigureAwait(false);
                    return;
                }
                catch
                {
                    idToken = string.Empty;
                    refreshToken = string.Empty;
                    uid = string.Empty;
                }
            }

            string url = $"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={ApiKey}";
            using var content = new StringContent("{\"returnSecureToken\":true}", Encoding.UTF8, "application/json");
            using HttpResponseMessage response = await Http.PostAsync(url, content).ConfigureAwait(false);
            string text = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
                throw new InvalidOperationException($"Firebase sign-in failed: {ExtractFirebaseError(text)}");

            using JsonDocument doc = JsonDocument.Parse(text);
            JsonElement root = doc.RootElement;
            idToken = ReadString(root, "idToken");
            refreshToken = ReadString(root, "refreshToken");
            uid = ReadString(root, "localId");
            long expiresSeconds = ReadLongString(root, "expiresIn", 3600L);
            tokenExpiresAtMs = UtcNowMs() + expiresSeconds * 1000L;

            if (string.IsNullOrEmpty(idToken) || string.IsNullOrEmpty(uid))
                throw new InvalidOperationException("Firebase anonymous sign-in returned an incomplete token.");
        }
        finally
        {
            authGate.Release();
        }
    }

    private async Task RefreshAuthTokenAsync()
    {
        string url = $"https://securetoken.googleapis.com/v1/token?key={ApiKey}";
        var values = new Dictionary<string, string>
        {
            ["grant_type"] = "refresh_token",
            ["refresh_token"] = refreshToken
        };
        using var content = new FormUrlEncodedContent(values);
        using HttpResponseMessage response = await Http.PostAsync(url, content).ConfigureAwait(false);
        string text = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Firebase token refresh failed: {ExtractFirebaseError(text)}");

        using JsonDocument doc = JsonDocument.Parse(text);
        JsonElement root = doc.RootElement;
        idToken = ReadString(root, "id_token");
        refreshToken = ReadString(root, "refresh_token");
        string refreshedUid = ReadString(root, "user_id");
        if (!string.IsNullOrEmpty(refreshedUid))
            uid = refreshedUid;
        long expiresSeconds = ReadLongString(root, "expires_in", 3600L);
        tokenExpiresAtMs = UtcNowMs() + expiresSeconds * 1000L;
    }

    private async Task<JsonElement?> GetDbJsonAsync(string path)
    {
        string text = await SendDbAsync(HttpMethod.Get, path, null).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(text) || string.Equals(text.Trim(), "null", StringComparison.Ordinal))
            return null;

        using JsonDocument doc = JsonDocument.Parse(text);
        if (doc.RootElement.ValueKind == JsonValueKind.Null)
            return null;
        return doc.RootElement.Clone();
    }

    private async Task<string> SendDbAsync(HttpMethod method, string path, object payload)
    {
        await EnsureAuthAsync().ConfigureAwait(false);
        string token = idToken;
        string cleanPath = (path ?? string.Empty).Trim('/');
        string url = $"{DatabaseUrl}{cleanPath}.json?auth={Uri.EscapeDataString(token)}";

        using var request = new HttpRequestMessage(method, url);
        if (payload != null)
        {
            string json = JsonSerializer.Serialize(payload);
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        }

        using HttpResponseMessage response = await Http.SendAsync(request).ConfigureAwait(false);
        string text = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Room service {(int)response.StatusCode}: {ExtractFirebaseError(text)}");
        return text;
    }

    private static RoomSnapshot ParseSnapshot(JsonElement root)
    {
        string hostUid = string.Empty;
        long revision = 0L;
        bool matchRunning = false;
        long matchElapsedMs = 0L;
        long matchStartedAtMs = 0L;
        var members = new List<RoomMemberSnapshot>();

        if (root.TryGetProperty("meta", out JsonElement meta) && meta.ValueKind == JsonValueKind.Object)
            hostUid = ReadString(meta, "hostUid");

        if (root.TryGetProperty("members", out JsonElement memberRoot) && memberRoot.ValueKind == JsonValueKind.Object)
        {
            foreach (JsonProperty property in memberRoot.EnumerateObject())
            {
                if (property.Value.ValueKind != JsonValueKind.Object)
                    continue;
                members.Add(new RoomMemberSnapshot(
                    property.Name,
                    SanitizeName(ReadString(property.Value, "name")),
                    NormalizeRole(ReadString(property.Value, "role"))));
            }
        }

        if (root.TryGetProperty("state", out JsonElement state) && state.ValueKind == JsonValueKind.Object)
        {
            if (state.TryGetProperty("revision", out JsonElement revisionElement) && revisionElement.ValueKind == JsonValueKind.Number)
                revisionElement.TryGetInt64(out revision);

            if (state.TryGetProperty("match", out JsonElement match) && match.ValueKind == JsonValueKind.Object)
            {
                if (match.TryGetProperty("running", out JsonElement runningElement)
                    && (runningElement.ValueKind == JsonValueKind.True || runningElement.ValueKind == JsonValueKind.False))
                    matchRunning = runningElement.GetBoolean();

                if (match.TryGetProperty("elapsedMs", out JsonElement elapsedElement) && elapsedElement.ValueKind == JsonValueKind.Number)
                    elapsedElement.TryGetInt64(out matchElapsedMs);

                if (match.TryGetProperty("startedAt", out JsonElement startedElement) && startedElement.ValueKind == JsonValueKind.Number)
                    startedElement.TryGetInt64(out matchStartedAtMs);
            }
        }

        members.Sort((a, b) =>
        {
            int aHost = string.Equals(a.Uid, hostUid, StringComparison.Ordinal) ? 0 : 1;
            int bHost = string.Equals(b.Uid, hostUid, StringComparison.Ordinal) ? 0 : 1;
            int hostCompare = aHost.CompareTo(bHost);
            return hostCompare != 0 ? hostCompare : string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase);
        });

        return new RoomSnapshot(hostUid, members, matchRunning, Math.Max(0L, matchElapsedMs), Math.Max(0L, matchStartedAtMs), revision);
    }

    private static RoomMemberSnapshot FindMember(RoomSnapshot room, string memberUid)
    {
        if (room == null || string.IsNullOrEmpty(memberUid))
            return null;
        foreach (RoomMemberSnapshot member in room.Members)
        {
            if (string.Equals(member.Uid, memberUid, StringComparison.Ordinal))
                return member;
        }
        return null;
    }

    private static bool HasOtherHider(RoomSnapshot room, string localUid)
    {
        if (room == null)
            return false;
        foreach (RoomMemberSnapshot member in room.Members)
        {
            if (!string.Equals(member.Uid, localUid, StringComparison.Ordinal)
                && string.Equals(member.Role, "hider", StringComparison.Ordinal))
                return true;
        }
        return false;
    }

    private static Dictionary<string, object> MemberPayload(string name, string role)
    {
        return new Dictionary<string, object>
        {
            ["name"] = SanitizeName(name),
            ["role"] = NormalizeRole(role),
            ["joinedAt"] = ServerTimestamp(),
            ["lastSeen"] = ServerTimestamp(),
            ["client"] = "native-0.0.25"
        };
    }

    private static object ServerTimestamp()
    {
        return new Dictionary<string, object> { [".sv"] = "timestamp" };
    }

    private static string RandomCode()
    {
        var builder = new StringBuilder(RoomCodeLength);
        for (int i = 0; i < RoomCodeLength; i++)
            builder.Append(RoomAlphabet[RandomNumberGenerator.GetInt32(RoomAlphabet.Length)]);
        return builder.ToString();
    }

    private static string NormalizeRole(string role)
    {
        return string.Equals(role, "hider", StringComparison.OrdinalIgnoreCase) ? "hider" : "seeker";
    }

    private string GetUid()
    {
        lock (stateLock)
            return uid;
    }

    private void SetStatus(string value)
    {
        lock (stateLock)
            status = value ?? string.Empty;
    }

    private void ClearRoomState(string newStatus)
    {
        lock (stateLock)
        {
            roomCode = string.Empty;
            connected = false;
            host = false;
            snapshot = null;
            status = newStatus;
        }
    }

    private static long UtcNowMs()
    {
        return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
    }

    private static string ReadString(JsonElement element, string property)
    {
        if (!element.TryGetProperty(property, out JsonElement value))
            return string.Empty;
        if (value.ValueKind == JsonValueKind.String)
            return value.GetString() ?? string.Empty;
        return value.ToString();
    }

    private static long ReadLongString(JsonElement element, string property, long fallback)
    {
        string value = ReadString(element, property);
        return long.TryParse(value, out long parsed) ? parsed : fallback;
    }

    private static string ExtractFirebaseError(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return "unknown error";
        try
        {
            using JsonDocument doc = JsonDocument.Parse(text);
            JsonElement root = doc.RootElement;
            if (root.TryGetProperty("error", out JsonElement error))
            {
                if (error.ValueKind == JsonValueKind.String)
                    return error.GetString() ?? "unknown error";
                if (error.ValueKind == JsonValueKind.Object && error.TryGetProperty("message", out JsonElement message))
                    return message.GetString() ?? "unknown error";
            }
        }
        catch
        {
        }
        return ShortError(text);
    }

    private static string ShortError(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return "unknown error";
        string cleaned = value.Replace('\r', ' ').Replace('\n', ' ').Trim();
        return cleaned.Length <= 120 ? cleaned : cleaned.Substring(0, 117) + "…";
    }

    public void Dispose()
    {
        disposed = true;
        authGate.Dispose();
        matchWriteGate.Dispose();
    }

    internal sealed class RoomSnapshot
    {
        public readonly string HostUid;
        public readonly IReadOnlyList<RoomMemberSnapshot> Members;
        public readonly bool MatchRunning;
        public readonly long MatchElapsedMs;
        public readonly long MatchStartedAtMs;
        public readonly long Revision;

        public RoomSnapshot(string hostUid, IReadOnlyList<RoomMemberSnapshot> members, bool matchRunning,
            long matchElapsedMs, long matchStartedAtMs, long revision)
        {
            HostUid = hostUid ?? string.Empty;
            Members = members ?? Array.Empty<RoomMemberSnapshot>();
            MatchRunning = matchRunning;
            MatchElapsedMs = matchElapsedMs;
            MatchStartedAtMs = matchStartedAtMs;
            Revision = revision;
        }
    }

    internal sealed class RoomMemberSnapshot
    {
        public readonly string Uid;
        public readonly string Name;
        public readonly string Role;

        public RoomMemberSnapshot(string uid, string name, string role)
        {
            Uid = uid ?? string.Empty;
            Name = name ?? "Player";
            Role = NormalizeRole(role);
        }
    }
}
