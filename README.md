# IMAX watcher

Checks the Premiere Cinemas page for Dune: Part Three every 15 minutes (GitHub Actions)
and pushes a phone notification via ntfy.sh as soon as an IMAX showing appears at
Premiere Plaza (Americana Plaza). The workflow switches itself off after it finds one.

- Secret `NTFY_TOPIC`: your ntfy topic name (subscribe to the same name in the ntfy app).
- Change the movie/cinema with the `MOVIE_URL` / `CINEMA` env vars in `watch.py`.
- Run now: Actions tab -> "Watch for IMAX" -> Run workflow.
