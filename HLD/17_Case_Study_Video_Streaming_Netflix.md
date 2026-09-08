# Session 17 — Case Study: Video Streaming Platform (Netflix) 🎬

> **Topics:** Challenges with video streaming · Adaptive Bitrate Streaming · Downsampling &
> chunking · HLS · Popular video platforms · Streaming pre-recorded videos
>
> 📄 Class doc: [\[SST-2028\] Case Study: Video Streaming — Netflix](https://docs.google.com/document/d/1FHxmMkLWDxiSz43qucIJxAK3Fl-yZCmGKPjxRwn_nNY/edit?usp=sharing)
> *(notes credited to **Pragy Agarwal**)*

---

## 📑 Table of Contents
1. [Challenges with Video Streaming](#-challenges-with-video-streaming)
2. [Adaptive Bitrate Streaming](#-adaptive-bitrate-streaming-abs)
3. [Downsampling](#1-should-all-clients-stream-at-the-same-resolution)
4. [Storage Cost — the 2× Result](#-the-2-storage-result)
5. [Picking the Right Resolution](#21-how-do-we-determine-the-best-resolution)
6. [Bandwidth Isn't Enough](#22-bandwidth-alone-is-not-enough)
7. [Detecting Bandwidth & Hardware](#23-how-do-we-get-the-clients-bandwidth--configuration)
8. [Chunking](#-chunking-the-video)
9. [Chunk Size Trade-off](#33-what-is-the-ideal-chunk-size)
10. [Monitoring Bandwidth for Free](#41-what-if-the-clients-bandwidth-changes-mid-stream)
11. [Just-in-Time Downloading](#42-just-in-time-chunk-downloading)
12. [HLS](#-https-live-streaming-hls)
13. [Popular Video Platforms](#-popular-video-platforms)
14. [System Design — Pre-recorded Video](#-streaming-pre-recorded-videos)
15. [Key Terms Recap](#-key-terms-recap)

---

## ⚠️ Challenges with Video Streaming

| Challenge | Detail |
|---|---|
| ⭐ **Video content is very large & bandwidth heavy** | **a video can range from a few 100 MBs to 10s of GBs** |
| ⭐ **Multiple clients can stream the same video at the same time** | For a popular Netflix show like **Game of Thrones**, there might be **hundreds of thousands of people streaming the same video simultaneously**. For **live content (like Cricket matches)** the concurrency numbers can be crazy — ⭐ **60M+ concurrent viewers for the India-Pak match** |
| ⭐ **Different clients have different hardware & software configurations** | **Screen resolutions:** 1080p @ 60 Hz, 2k @ 144 Hz, 4k @ 144 Hz, … · **CPU/GPU:** ARM chips, desktop CPUs, integrated graphics, gaming GPUs, **custom TV chipsets** |
| ⭐ **Different clients have different network bandwidths** | **1 Mbps to 1 Gbps** |
| ⭐ **Internet speed of the SAME client can vary over time** | **Especially for mobile users** — connecting to a different tower, or ⭐ **entering a Faraday Shield** (inside an elevator, under a flyover, …) can cause internet speeds to suffer. **But also for smart-TV / desktop users**, because they might share a network connection with others |

> 🧠 **Note the shape of the problem.** Every other case study in this course scaled on *requests*.
> Video scales on **bytes** — and the client's capacity to receive those bytes is **heterogeneous
> and changes mid-request**. That's what makes it a genuinely different design.

---

## 📶 Adaptive Bitrate Streaming (ABS)

## 1. Should all clients stream at the same resolution?

> ⭐ **No!** Different clients have different internet speeds. If we force all clients to:
> - ⭐ **Stream at the highest resolution** — **clients with slower bandwidth will suffer, since
>   their video will "BUFFER"**
> - ⭐ **Stream at the lowest resolution** — 😄 **clients with higher bandwidths won't be able to
>   enjoy their cat videos**

> ⭐⭐ **Solution: we should serve DIFFERENT RESOLUTIONS to different clients based on their
> bandwidths!**

### Downsampling
> ⭐ **Pre-process (in the backend) the uploaded video to various resolutions & fps.**

```
input
  one_piece_1080p_60fps.mp4

output
  one_piece_720p_60fps.mp4    one_piece_720p_30fps.mp4
  one_piece_480p_60fps.mp4    one_piece_480p_30fps.mp4
  one_piece_360p_60fps.mp4    one_piece_360p_30fps.mp4
  one_piece_240p_60fps.mp4    one_piece_240p_30fps.mp4
```

> ⭐ **This is called DOWNSAMPLING.**
> **Could you also UPSAMPLE the video?** ⭐ **Nope.** *(maybe with AI — **it will still be a lie**)*

> 💡 **The reason upsampling is impossible is information-theoretic** — the detail was never
> captured. AI upscaling *invents* plausible detail; it does not recover the original.

---

## 💾 The 2× Storage Result

> **Q: Won't this increase the amount of storage required in the backend by several times?**
>
> - ⭐ **Storage is cheap — you shouldn't worry about it**
> - **At the scale of YouTube it starts mattering** — ⭐ **YouTube stores more than 1 exabyte!**
> - ⭐ **Actually Netflix's content repository is much smaller** *(a few thousand titles vs
>   user-generated content)*
> - ⭐ **Lower resolutions also require drastically lower storage:**
>   - **2 hour video at 8k @ 60 fps** might be **15 GB** in size (compressed)
>   - **2 hour video at 1080p @ 30 fps** might be only **1.5 GB** in size (compressed)

### The elegant bound ⭐⭐
> **Overall, if you add the file sizes for all the downsampled resolutions, your total storage
> requirement will grow to only ~2×:**
```
1 + ½ + ¼ + ⅛ + …  =  2
```

> ⭐⭐ **This is the key insight.** Each step down in resolution roughly **halves** the file size, so
> the whole ladder of variants is a **geometric series that converges to 2**. You get every
> resolution for **double** the storage of the original — not 8× as intuition suggests.

---

## 2.1. How do we determine the best resolution?

> ⭐ **In the frontend, we can monitor the client's bandwidth, and serve the highest resolution that
> will not buffer on their bandwidth.**
>
> **Maintain a mapping of bandwidth → resolution:**

| Resolution | Required Bandwidth (H264) |
|---|---|
| **720p — 1280×720 (HD)** | ⭐ **3 Mbps** |
| **1080p — 1920×1080 (FHD)** | ⭐ **6 Mbps** |
| **2160p / 4K — 3840×2160 (UHD)** | ⭐ **25 Mbps** |

> - ⭐ **Note: actual requirements will depend on the VIDEO CODEC.** For example, **H265 requires
>   almost ½ the bandwidth compared to H264**
> - ⭐ **Note: you typically don't want to ENFORCE a resolution on the client — you just detect and
>   configure the "DEFAULT" resolution, but the client should be able to OVERRIDE this via
>   preferences**

---

## 2.2. Bandwidth alone is not enough

> **Q: Given a client that has a 1 Gbps network & a 720p screen, should we serve them a video at
> 1080p?** *The client's bandwidth can handle 1080p easily — so yes?*
>
> ⭐⭐ **No!** **Screen supports max 720p resolution, so there's no point in serving a higher
> resolution to the client — it will just WASTE THEIR DATA PACK.**
> ⭐ **In fact, the client's CPU/GPU will have to work HARDER to downsample the 1080p video to a 720p
> screen.**

> ⭐ **The actual resolution that the client sees should depend not only on the bandwidth, but also on
> the hardware configuration:**

| Factor | Why |
|---|---|
| ⭐ **CPU/GPU** | **video decoding requires intensive processing. High resolution videos can "STUTTER" on low-end devices** |
| ⭐ **Screen Size & Refresh rate** | **we should not serve at a resolution or fps that is higher than what the client's screen supports** |
| ⭐ **Software configuration** | **depending on the browser & video codecs installed, we might want to serve video in different formats** |

```
   ⭐ Serve  min( bandwidth allows, screen supports, CPU/GPU can decode )
      …and let the user override it.
```

---

## 2.3. How do we get the client's bandwidth & configuration?

### Bandwidth — a speed test
> ⭐ **Perform a speed test:**
> 1. **download a junk (random) file of known size**
> 2. **measure the time it took for the download to complete**
> 3. **bandwidth = file size / time**
>
> *e.g. a **100 MB** file takes **10 seconds** to download ⇒ the bandwidth is **10 MBps***

### Hardware & Software Configuration
| Technique | Detail |
|---|---|
| ⭐ **User Agent detection** | `console.log(navigator.userAgent)` → `'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'` |
| ⭐ **Device Fingerprinting** | **cookies, operating system, http headers, laptop battery %, user behaviour (clicks, mouse movements, keyboard strokes)** … lots of other stuff |

**Try it:** *My Fingerprint — Am I Unique?* · *Browser Fingerprint*

---

## 🧩 Chunking the Video

### 3.1. Should we download the entire video before playing?
> ⭐ **Long videos at high resolutions can have very large file sizes (10s of GBs). If we download the
> entire video before playback, the client will have to wait for a long time.**
>
> ⭐ **Instead, we should "STREAM" the video — play the video as it is being downloaded.**

### 3.2. What if the client "seeks" forward/backward?
> **Suppose a client starts watching a video, but skips to the 30 min mark. How do we handle that?**

| Naive option | Problem |
|---|---|
| **Re-download the entire video from scratch?** | ⭐ **That will be a waste of bandwidth, and will require a lot of time** |
| **Download video from that timestamp** | ⭐ **But the video is a BINARY file — how do we know the BIT OFFSET from the timestamp?** |

> 😱 **For scale: a 2 hour movie @ 8k resolution @ 60 fps will cost you ~43 TB in the RAW format!**

### The solution — chunking ⭐
> ⭐⭐ **Chunk the video (at each resolution) into small sections.**

```
input
  one_piece_1080p_60fps.mp4

output
  one_piece_720p_60fps_chunk_01.mp4    one_piece_720p_30fps_chunk_01.mp4
  one_piece_720p_60fps_chunk_02.mp4    one_piece_720p_30fps_chunk_02.mp4
  one_piece_720p_60fps...              one_piece_720p_30fps...
  one_piece_720p_60fps_chunk_20.mp4    one_piece_720p_30fps_chunk_20.mp4
  one_piece_480p_60fps_chunk_01.mp4    one_piece_480p_30fps_chunk_01.mp4
  ...
  one_piece_360p_60fps_chunk_20.mp4    one_piece_360p_30fps_chunk_20.mp4
```

### The playback algorithm ⭐
> 1. **Client tries to watch the video**
> 2. **Video player on the frontend will determine the "best" resolution to serve the video at**
> 3. **Video player (client side) will download the FIRST CHUNK at the appropriate resolution**
> 4. **Once the first chunk is downloaded, video playback will start — the video player starts
>    playing this chunk**
> 5. ⭐ **While the video playback continues, the video player keeps downloading the next chunks**
> 6. ⭐ **If the client seeks forward to a specific timestamp, we can directly request the last chunk
>    starting before or at that timestamp**
> 7. ⭐ **Any chunk that is downloaded will remain in the BROWSER CACHE — allows the client to seek to
>    an older timestamp without re-buffering**

```
   timeline:  [c01][c02][c03][c04][c05][c06][c07]…[c20]
                            ▲                ▲
                       playing here     seek to 30 min → ⭐ just fetch c14 directly
   ⭐ chunking turns "byte offset in a binary blob" into "which file do I want"
```

> 🧠 **Chunking solves three problems at once:** instant playback start, seeking, **and** the ability
> to switch resolution mid-stream (next section). One idea, three wins.

---

## 3.3. What is the ideal chunk size?

> **Should we chunk by number of bits (10 MB / 100 MB …)? Or by time duration (10 sec / 1 min)?**

### Implications of chunk size ⭐
| Chunk size | Consequence |
|---|---|
| ⭐ **Higher** | **more INITIAL BUFFERING**, since the client has to wait longer to download the 1st chunk |
| ⭐ **Lower** | **more N/W REQUESTS**, since each chunk has to be downloaded separately |

> ⭐ **Ideal chunk size will depend on the application** *(more on this later)*.

---

## 4.1. What if the client's bandwidth changes mid-stream?

> ⭐ **We should continuously monitor the client's bandwidth. But how? Should we regularly download
> junk files to measure the bandwidth? If we do this, won't we end up wasting precious bandwidth and
> data?**

### The free measurement ⭐⭐
> ⭐⭐ **As the chunks are being downloaded, we can measure the time taken for download. Since each
> chunk has a KNOWN BYTE SIZE (stored in the file metadata), we can calculate the bandwidth
> CONTINUOUSLY!**
>
> ⭐ **Note: each chunk has the SAME DURATION (say 10 s), but DIFFERENT FILE SIZES (based on how
> complex the video scene is).**
>
> ⭐ **Each next chunk will be downloaded at the appropriate resolution, given the latest bandwidth.**
>
> ⭐ **Note that all this calculation & bandwidth monitoring is happening on the CLIENT SIDE.**

```javascript
async getChunk(url: string): Promise<{data: ByteArray[], size: integer, timeMs: integer}> {
     startTime = new Date()
     response = await get(url => …)
     timeMs = new Date() - startTime()
}
```

> 💡 **This is beautiful engineering:** the speed test isn't a separate cost — **the payload IS the
> probe.** Every chunk you had to download anyway doubles as a bandwidth measurement. Zero waste.

---

## 4.2. Just-in-Time chunk downloading

> **Should we download the next chunk immediately after the previous one is downloaded?**
> ⭐ **No. Most people don't watch the entire video — they skip ahead, or switch to another video.**
>
> ⭐⭐ **We should download the next chunk "JUST IN TIME" — download the next chunk when:**
> ```
> remaining-playback-time  ≤  (time-to-download-next-chunk + x% buffer)
> ```
> ⭐ **By the time the user reaches the end of the available playback, the next chunk should be
> available — so that we don't waste any bandwidth, and the client doesn't need to buffer.**

```
   ⭐ Too eager  → wasted bandwidth (user abandons the video)
   ⭐ Too late   → buffering (bad UX)
   ⭐ Just in time → neither
```

> 🧠 **Note the business motivation:** the reason to be lazy isn't elegance — it's that
> **pre-downloading a video nobody finishes is pure money burned on CDN egress**, at Netflix scale.

---

## 📺 HTTP(s) Live Streaming (HLS)

> - ⭐ **HTTP(s)-based Adaptive Bitrate Streaming protocol, introduced by Apple in 2009**
> - ⭐ **Uses XML-based `.m3u8` files**
> - ⭐ **Most popular video streaming protocol (as of 2026)**
> - **Supports encryption & copyright protection**
> - **Supports ads, section markers (intro, credits, …), thumbnails, …**

### The two-level playlist structure ⭐

**Level 1 — the master `.m3u8` (lists the variants):**
```
#EXTM3U
#EXT-X-VERSION:1
## Created with Unified Streaming Platform  (version=1.13.0-29687)

# variants
#EXT-X-STREAM-INF:BANDWIDTH=493000,CODECS="mp4a.40.2,avc1.66.30",RESOLUTION=224x100,FRAME-RATE=24
tears-of-steel-audio_eng=64008-video_eng=401000.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=932000,CODECS="mp4a.40.2,avc1.66.30",RESOLUTION=448x200,FRAME-RATE=24
tears-of-steel-audio_eng=128002-video_eng=751000.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1197000,CODECS="mp4a.40.2,avc1.77.31",RESOLUTION=784x350,FRAME-RATE=24
tears-of-steel-audio_eng=128002-video_eng=1001000.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1727000,...,RESOLUTION=1680x750,FRAME-RATE=24,VIDEO-RANGE=SDR
tears-of-steel-audio_eng=128002-video_eng=1501000.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2468000,...,RESOLUTION=1680x750,FRAME-RATE=24,VIDEO-RANGE=SDR
tears-of-steel-audio_eng=128002-video_eng=2200000.m3u8

# audio-only variants
#EXT-X-STREAM-INF:BANDWIDTH=68000,CODECS="mp4a.40.2"
tears-of-steel-audio_eng=64008.m3u8
```
> ⭐ **Note each variant declares its `BANDWIDTH`, `CODECS`, `RESOLUTION` and `FRAME-RATE`** — exactly
> the information the client needs to make the decision from section 2.2. **The protocol hands the
> client the menu; the client chooses.**

**Level 2 — a specific resolution's `.m3u8` (lists the chunks):**
```
#EXTM3U
#EXT-X-VERSION:1
#EXT-X-MEDIA-SEQUENCE:1
#EXT-X-TARGETDURATION:4
#USP-X-TIMESTAMP-MAP:MPEGTS=900000,LOCAL=1970-01-01T00:00:00Z
#EXTINF:4, no desc
tears-of-steel-audio_eng=128002-video_eng=2200000-1.ts
#EXTINF:4, no desc
tears-of-steel-audio_eng=128002-video_eng=2200000-2.ts
#EXTINF:4, no desc
tears-of-steel-audio_eng=128002-video_eng=2200000-3.ts
...
#EXTINF:4, no desc
tears-of-steel-audio_eng=128002-video_eng=2200000-183.ts
#EXTINF:2, no desc
tears-of-steel-audio_eng=128002-video_eng=2200000-184.ts
#EXT-X-ENDLIST
```
> ⭐ **`#EXTINF:4` = each chunk is 4 seconds** (note the **last chunk is 2 s** — the remainder).
> **`.ts` files are the actual binary chunks** and can be played directly in a video player.

**Live demo URLs (from the class doc):**
- Base: https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8
- 1680×750 @ 24 fps: `.../tears-of-steel-audio_eng=128002-video_eng=2200000.m3u8`
- 1st chunk: `.../tears-of-steel-audio_eng=128002-video_eng=2200000-1.ts`

### Resources (optional)
- *Introduction to HTTP Live Streaming: HLS on Android and More* — Toptal
- *HLS in Depth*
- Sample files: *Free HLS m3u8 URLs for Testing HLS Players* — OTTVerse
- *Incorporating Ads into a Playlist* — Apple Developer Documentation

---

## 🎥 Popular Video Platforms

Categorising the problem space — **because the design differs enormously by category.**

### Pre-recorded Videos
| Platform | Characteristics |
|---|---|
| **YouTube / Vimeo / Dailymotion** | **User uploaded content** · both **short (10s) & long form (10min+)** videos, **but mostly long form** · **pre-recorded majorly** |
| **TikTok / Instagram / Facebook videos** | **User uploaded content** · ⭐ **primarily short form (10s)** videos · pre-recorded majorly |
| ⭐ **Netflix** | ⭐ **Production house content** (movies/shows) · ⭐ **very long form (1 hour+)** · ⭐ **high concurrency (100,000+ users within a few hours for popular shows)** |

### Live Videos — High Concurrency, High latency
| Platform | Characteristics |
|---|---|
| **Twitch** | **User uploaded content** · **live streaming majorly** · ⭐ **latency streamer → audience is decent (10+ seconds)** · **high concurrency (50,000 concurrent viewers on top streams)** |
| ⭐ **Hotstar / Sony Live** | **Production house content** · **live coverage of important sports (cricket / football)** · ⭐⭐ **ultra-high concurrency for live streaming (60M+ concurrent users watching the same stream live!)** |

### Live Videos — Low Concurrency, Low Latency
| Platform | Characteristics |
|---|---|
| **Google Meet / Zoom** | **Realtime streaming** · ⭐ **very low latency (< 3 seconds)** · **multiple people streaming video together** · **max 100 to 1000 audience members** |
| **Scaler Live classes (Agora)** | **Realtime streaming** · **very low latency (< 3 s)** · **single person streaming** · **max 10,000 audience members** |
| **WhatsApp / Teams / Slack video calls / TeamViewer / UltraViewer** | ⭐ **Peer to peer** · ⭐ **ultra low latency (~1 second)** |

```
   ⭐ THE TRADE-OFF AXIS:
      concurrency ▲
       60M  │ Hotstar (live cricket)          ← high concurrency, high latency (10s+)
       50K  │ Twitch
      100K  │ Netflix (pre-recorded)
       1K   │ Zoom / Meet                     ← low concurrency, LOW latency (<3s)
        2   │ WhatsApp call (P2P)             ← ~1 s
            └──────────────────────────▶ latency tolerance
      ⭐ You cannot have 60M viewers AND 1-second latency.
```

> 🧠 **This taxonomy is the real answer to "design a video platform".** The first question in the
> interview should be **which quadrant** — pre-recorded vs live, and how many concurrent viewers.
> Netflix (pre-recorded, high concurrency) is the easiest of the four; **P2P calls and 60M-viewer
> live streams are entirely different systems.**

---

## 🏗️ Streaming Pre-recorded Videos

> **YouTube / Netflix / JioCinema**

### Step 1 — Content creator uploads the video
> **The video is uploaded at the upload microservice, which stores it in the database.**

**Ideal database?**
| Data | Store |
|---|---|
| ⭐ **video** | ⭐ **Large File Store (S3)** |
| ⭐ **metadata** | ⭐ **SQL** *(or a Doc DB if there's too much data)* |

**Why SQL for metadata?**
> - ⭐ **schema:** for each `video_id` store **chunk ids, resolutions, corresponding chunk URLs,
>   uploader information**, and any other metadata about the video
> - ⭐ **joins:** *given the `uploader_id`, find all videos by them*
> - ⭐ **complex queries:** *find all 720p videos uploaded in the last 1 hour*

*(Session 15: object stores for the bytes, a relational DB for the relationships.)*

### Step 2 — Video is processed into multiple resolutions (downsampling & chunking)
> ⭐ **Apart from inserting the video into S3 & metadata into SQL, the upload service will also insert
> a task in a MESSAGE QUEUE.**
>
> ⭐ **The Downsampling service picks tasks from the message queue. For each task:**
> 1. **Fetch Video from FileStore, fetch Metadata from SQL**
> 2. **Downsample the video to various resolutions**
> 3. **Chunk each video into multiple segments**
> 4. **Upload the chunks to the file store**
> 5. **Create & store metadata for all these chunks in SQL**

> 💡 **Why a queue?** Transcoding a 2-hour film into 8 resolutions is **CPU-bound work taking
> minutes to hours** — it can never sit on the request path. *(And per Session 5: never
> multi-thread CPU-bound work — you scale it out with more workers instead.)*

### Step 3 — Serving the video to clients
> **We need to serve both the video chunks (`.ts` files) & the metadata (`.m3u8` file).**
>
> **Should the clients download the video chunks from our file storage service?**
> ⭐⭐ **No! File Storage Services like S3 are NOT optimized for fast reads/writes at high scale.
> Instead the user will download the chunks from the CDN (ALWAYS).**
>
> ⭐⭐ **"CDNs perform the heavy lifting for serving videos @ scale."**

**What about the metadata?**
> - ⭐ **If the metadata (`m3u8`) file is STATIC, it can also be served from the CDN**
> - ⭐ **However, it can be DYNAMIC as well:**
>   - ⭐ **dynamic advertisement injection**
>   - ⭐ **geolocation based content personalization**
> - ⭐ **In such cases we have to "CONSTRUCT" the `m3u8` for each request via a backend app server.
>   The app server can depend on a CACHING LAYER to store the constructed `m3u8`, instead of fetching
>   the metadata from the SQL db & reconstructing the file every time**

```
   Upload:  Creator ──▶ [Upload svc] ──▶ S3 (raw video)  +  SQL (metadata)
                              │
                              └──▶ [Message Queue] ──▶ [Downsampling svc]
                                                            │ downsample + chunk
                                                            ▼
                                                 S3 (all chunks) + SQL (chunk metadata)
                                                            │
   Playback:                                                ▼
   Client ──▶ app server (constructs .m3u8, ⭐ cached) ─────┐
          └──▶ ⭐ CDN ──▶ .ts chunks  ◀─────────────────────┘ (origin: S3)
```

### Ideal Chunk size (for pre-recorded content) ⭐
> - ⭐ **For pre-recorded content, the chunk sizes can be LARGER — typically kept between 5 s to 10 s
>   to reduce the number of network calls**
> - ⭐⭐ **"Apple recommends 6s chunk size for HLS"**
> - **In some services the chunk size can be as large as 1 minute**
> - ⭐ **Scaler Recorded Video (not live class) has a chunk size of 16.5 s**

> 💡 **Why pre-recorded can afford big chunks:** there's no live edge to catch up to. For **live**
> streaming, chunk size *is* your latency floor — a 6-second chunk means you're **at least 6 seconds
> behind reality**, which is exactly why Twitch sits at 10+ seconds and Zoom (needing <3 s) cannot
> use HLS at all.

---

## 📝 Key Terms Recap

| Term | One-line meaning |
|---|---|
| **Buffering** | Playback stalls because the next bytes haven't arrived |
| ⭐ **Adaptive Bitrate Streaming (ABS)** | Serve **different resolutions to different clients** based on their bandwidth |
| ⭐ **Downsampling** | Pre-process the upload into many lower resolutions/fps. ⭐ **Upsampling is impossible** |
| ⭐ **The 2× rule** | ⭐⭐ `1 + ½ + ¼ + … = 2` — **all variants together cost only ~2× the original** |
| **Bandwidth ladder (H264)** | ⭐ **720p → 3 Mbps · 1080p → 6 Mbps · 4K → 25 Mbps**; **H265 needs ~½** |
| ⭐ **Resolution = min(bandwidth, screen, CPU/GPU)** | ⭐ And **never enforce** — set a default the user can override |
| **Speed test** | Download a junk file of known size; `bandwidth = size / time` |
| **User agent / fingerprinting** | How the client's hardware & software config is detected |
| ⭐ **Chunking** | Split each resolution into small segments ⇒ **instant start, seeking, mid-stream resolution switching** |
| **Browser cache of chunks** | ⭐ Lets the user seek **backwards** without re-buffering |
| **Chunk size trade-off** | ⭐ **Bigger ⇒ more initial buffering; smaller ⇒ more network requests** |
| ⭐ **Free bandwidth monitoring** | ⭐⭐ **Each chunk's known byte size ÷ its download time** — the payload is the probe |
| **Constant duration, variable size** | ⭐ Chunks are the same **seconds** but different **bytes** (scene complexity) |
| ⭐ **Just-in-Time download** | Fetch the next chunk when `remaining playback ≤ download time + buffer%` — avoids wasting egress on abandoned videos |
| ⭐ **HLS** | Apple, 2009; `.m3u8` playlists + `.ts` chunks; **most popular protocol as of 2026** |
| **Master vs media playlist** | The master lists **variants** (bandwidth/resolution/codec); each media playlist lists **chunks** |
| **Platform quadrants** | ⭐ pre-recorded vs live × high vs low concurrency — ⭐ **Hotstar 60M live viewers; Zoom <3 s; P2P ~1 s** |
| ⭐ **CDNs do the heavy lifting** | ⭐⭐ **Never serve chunks from S3** — S3 isn't optimised for high-scale reads |
| **Dynamic `m3u8`** | Constructed per request (ads, geo-personalisation) and **cached** |
| **Recommended chunk size** | ⭐ **Apple recommends 6 s**; 5–10 s typical; Scaler uses **16.5 s** for recordings |

---

## 🎯 Session Takeaways

1. ⭐ **Video is a bytes problem, not a requests problem** — and the client's capacity is
   **heterogeneous and varies mid-stream** (towers, elevators, shared Wi-Fi).
2. ⭐ **One resolution for everyone fails both ways** — the slow client buffers, the fast client is
   short-changed. Hence **Adaptive Bitrate Streaming**.
3. ⭐ **Downsample on upload; you can never upsample.** AI upscaling invents detail, it doesn't
   recover it.
4. ⭐⭐ **All resolution variants cost only ~2× the original storage**, because each step halves the
   size and `1 + ½ + ¼ + … = 2`.
5. ⭐ **Resolution = min(bandwidth allows, screen supports, CPU/GPU can decode)** — serving 1080p to a
   720p screen wastes the user's data *and* their CPU. Always let the user override.
6. ⭐⭐ **Chunking solves three problems with one idea:** playback starts after one chunk, seeking
   becomes "fetch chunk N", and resolution can change **between** chunks.
7. ⭐ **Cached chunks in the browser** make backwards seeking free.
8. ⭐⭐ **Measure bandwidth for free** — each chunk has a known byte size, so download time *is* a
   speed test. No junk downloads needed, and it all happens **client-side**.
9. ⭐ **Chunks are constant in duration but variable in size** (scene complexity).
10. ⭐⭐ **Download just-in-time**, not eagerly — most users abandon videos, and pre-fetching burns CDN
    egress for nothing.
11. ⭐ **HLS (Apple, 2009) is the dominant protocol:** a master `.m3u8` advertises variants, each media
    `.m3u8` lists `.ts` chunks. The **protocol hands the client a menu and lets it choose.**
12. ⭐ **Classify the platform first** — pre-recorded vs live, high vs low concurrency. 60M concurrent
    live viewers and sub-second P2P calls are **different systems**, not different settings.
13. ⭐ **Architecture:** S3 for bytes + SQL for metadata + **message queue → downsampling workers**
    (CPU-bound, off the request path) + ⭐⭐ **CDN for all chunk delivery** — never S3 directly.
14. ⭐ **Chunk size is the dial:** 5–10 s (Apple recommends **6 s**) for pre-recorded, because for
    **live** streaming chunk size becomes your **latency floor**.

---

## ➡️ Next
**[Session 18 — Case Study: Cab Booking Application (Uber)](./18_Case_Study_Uber_and_QuadTrees.md)**
