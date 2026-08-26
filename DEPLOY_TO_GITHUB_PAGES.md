# Deploy Big Walk Hide + Seek to GitHub Pages

This folder is ready to upload directly to a GitHub repository.

## One-time setup

1. Create a new GitHub repository, for example `big-walk-hide-seek`.
2. Upload **the contents of this folder** to the repository root. `index.html` should be at the root, not inside another folder.
3. Open the repository's **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Choose your main branch (usually `main`) and the root folder `/`.
6. Save. GitHub will publish the static site.

## Future updates

For future site versions, replace the repository files with the new build and commit/push them. GitHub Pages republishes when the publishing branch changes.

The site checks `version.json` with caching disabled. If someone has an older page open while a newer version is deployed, an **Update available** banner can appear; clicking **Reload latest** forces a fresh load.

## Live location on the hosted site

Install **BigWalkLivePosition v0.2.1**. The hosted HTTPS page connects only to the local bridge at `127.0.0.1:32145`.

A modern browser may ask permission for local/loopback network access. Allow it. Your coordinates stay on your computer; the plugin listens only on the loopback interface and the static website does not contain a server that receives them.
