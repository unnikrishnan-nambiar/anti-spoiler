# One-minute public browser scan

The requested scan ran for **60.004 seconds**, visiting four public pages: the supplied reel, `alabolelo_song`'s profile, its linked audio page, and one additional reel discovered through the public links. No login, CAPTCHA, privacy restriction or platform limit was bypassed. This is limited public coverage, not a scan of all Instagram.

Two related reel URLs were observed:

- https://www.instagram.com/reel/DcTxhjWiS11/ — caption: “ALA BOLELO SONG … JAILER 2”; audio label: “Ala Bolelo”. This is the user's original link.
- https://www.instagram.com/reel/DcTbN_gi9Tb/ — caption: “ALA BOLELO SONG JAILER 2 OUT NOW … JAILER 2”; audio label: “Original audio”. This is the additional public link discovered in the scan.

Both belong to `alabolelo_song`. **Neither is a verified match to the uploaded video.** Public logged-out pages exposed posters, not playable video/audio. Two visible poster captures were compared against all 121 indexed reference keyframes using ORB/RANSAC and pHash. Neither produced accepted geometric correspondence (similarity 0, zero accepted inliers). A poster mismatch does not prove the reel's video is unrelated. One additional reel poster capture timed out; no match is inferred from that failure.

Eight local eight-second snippets were created at reference offsets 0, 30, 60, 90, 120, 150, 180 and 210 seconds. Their manifest includes hashes and measured durations. They are reference artifacts, not Instagram detections. No full reel audio/video was compared against those snippets because the logged-out browser supplied no playable candidate.

Laya was not used to produce this scan's findings. Its SDK interface is now verified and an optional evidence adapter exists, but the model-weight download is blocked; see [LAYA.md](LAYA.md). The observed public links are metadata candidates, with no detection confidence assigned.

Machine-readable browser logs and captured images are retained privately under `.local/instagram-browser/one-minute/`. Snippets are under `.local/snippets/user-reference-38/`.
