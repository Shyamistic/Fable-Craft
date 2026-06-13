# Fablecraft

**Fablecraft** transforms a child's drawing into a narrated, illustrated 8-scene quest (story adventure), augmenting imagination with Generative AI. Children draw characters, watch them come to life, and play through interactive stories that teach life lessons and values.

---

## Try Fablecraft Live

You can access the hosted version of **Fablecraft** here:  
[Open Fablecraft Web App](#) *(deployment URL will be added after deploy)*

> **Best viewed on:** Desktop or iPad (tablet and desktop viewports 768px–1920px).

### Runtime Notes
- Character generation: ~15 seconds
- Quest generation: ~2.5 minutes
  _(Actual times may vary depending on model loads and network conditions.)_

---

## High-Level System Overview

Fablecraft consists of two main components:

- **Next.js Frontend (UI Service):** Built for the browser, the interface lets children draw directly on a digital canvas — whether on a tablet or a computer. They can also upload photos of their favorite toys, stuffed animals, or hand-drawn art to turn them into story characters.
- **FastAPI Backend (Agents Service):** The backend orchestrates multiple AI services — Vision Analyzer, Quest Engine, Character Generator, Scene Illustrator — to generate characters, stories, and illustrations.

An optional **Text-to-Speech** endpoint provides narrated playback using Amazon Polly Neural voices.

---

## Cloud Deployment Surfaces

| Component | Technology | Deployment | Purpose |
|-----------|------------|------------|---------|
| **Frontend** | Next.js | AWS Amplify | Drawing canvas, story flow UI |
| **Backend** | FastAPI | ECS Fargate | Orchestrates AI services |
| **Media** | Amazon S3 + CloudFront | – | Stores all uploads & generated assets |
| **AI Services** | Amazon Bedrock (Claude + Titan/Stability) & Amazon Polly | – | Drawing analysis, story generation, image synthesis, narrations |

The frontend and backend are containerized with dedicated **Dockerfiles** and deployable on AWS infrastructure. Runtime dependencies include **Amazon S3**, **Amazon Bedrock**, and **Amazon Polly**.

---

## How the Workflow Works

Transforming a child's character and lesson into a fully illustrated, interactive picture book is a complex process divided into specialized services.

### 1. Creating Your Character (Vision Analyzer + Character Generator)

When a child finishes their drawing and hits "Generate Character":

1. The frontend sends the base64-encoded drawing and a session ID to the `/api/characters/generate` endpoint.
2. The backend uploads the image to **Amazon S3** and runs **Vision Analysis** via Amazon Bedrock Claude.
3. The Vision Analyzer extracts character attributes (type, colors, style, mood) and checks content safety.
4. The Character Generator produces a child-friendly animated character image via Bedrock image generation.
5. The response includes structured character data and CDN URLs for both images.

### 2. Choosing a Lesson & Genre

The child (or parent) selects one of 12+ predefined life lessons (sharing, kindness, honesty, etc.) or types a custom lesson. They also pick a story genre (Fantasy Kingdom, Outer Space, Underwater World, Jungle Safari).

### 3. Quest Generation (Quest Engine + Scene Illustrator)

1. The frontend sends character metadata, lesson, and genre to `/api/quests/generate`.
2. The **Quest Engine** (powered by Amazon Bedrock Claude) generates an 8-scene interactive story with questions and choices.
3. The **Scene Illustrator** produces storybook-style illustrations for each scene in batches.
4. The complete quest is rendered in the frontend UI as an interactive picture book.

### 4. Adding Narration with Text-to-Speech (Optional)

To make stories more immersive and accessible:

1. The frontend sends story text to `/api/tts/synthesize`.
2. The backend invokes **Amazon Polly Neural** to generate child-friendly MP3 narration.
3. The audio file is stored in S3, and the returned URL enables scene-by-scene playback.

---

## Features

- 🎨 **Drawing Canvas** — Freehand drawing with 20 colors, adjustable brush, eraser, undo
- 📷 **Image Upload** — Upload PNG, JPG, or WEBP images up to 5 MB
- 🤖 **AI Character Generation** — Turn drawings into animated characters
- 📖 **Interactive Quests** — 8-scene stories with questions and choices
- 🎓 **Life Lessons** — 12+ predefined lessons plus custom lesson support
- 🌍 **Story Genres** — 4 themed worlds for different adventures
- 🔊 **Text-to-Speech** — Optional narrated playback for all story text
- 🖼️ **Character Gallery** — Save and reuse up to 50 characters
- 👨‍👩‍👧 **Parent Dashboard** — PIN-protected stats and progress tracking
- 👫 **Collaborative Mode** — Two children play through a shared story quest
- 📊 **Analytics** — Novus.ai integration for anonymous engagement tracking
- ♿ **Accessible** — COPPA-compliant, responsive, child-safe content filtering

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, Pydantic |
| AI / ML | Amazon Bedrock (Claude, Titan/Stability), Amazon Polly |
| Storage | Amazon S3, CloudFront CDN |
| Analytics | Novus.ai SDK |
| Hosting | AWS Amplify (frontend), ECS Fargate (backend) |

---

## Getting Started (Local Development)

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd agents_service
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Set environment variables for AWS credentials, Bedrock model IDs, and S3 bucket name. See `agents_service/config.py` for all configurable values.

---

## License

MIT
