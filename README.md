# Ask Alma

A Retrieval-Augmented Generation (RAG) system for answering questions about Columbia College, Columbia Engineering, and Barnard College. AskAlma helps students with course planning, professor reviews, academic requirements, and registration guidance using course bulletins and student reviews.

## Overview

AskAlma is a full-stack web application that combines:
- **Semantic search** using OpenAI's `text-embedding-3-small` model
- **Vector database** (Supabase PostgreSQL with pgvector) for efficient similarity search
- **LLM generation** using OpenAI's GPT models for natural language responses
- **User profiles** to personalize responses based on academic context
- **Conversation history** for contextual follow-up questions

The system can answer questions about:
- Course information (descriptions, prerequisites, credits, when offered)
- Professor reviews and teaching styles
- Major and minor requirements
- Core Curriculum requirements
- Academic policies and registration procedures
- Semester planning and course recommendations

## Features

### Personalized Academic Guidance
- **User Profiles**: Students can set their school, academic year, major, minors, and completed courses
- **Context-Aware Responses**: AskAlma uses profile information to:
  - Prioritize school-specific information (Barnard, Columbia College, SEAS)
  - Avoid recommending courses already completed
  - Tailor recommendations to academic year and major requirements

### Conversational Interface
- **Chat History**: Conversations are saved and can be resumed
- **Conversation Management**: List, search, rename, and delete conversations
- **Contextual Follow-ups**: The system maintains conversation context for natural dialogue
- **Typing Animation**: Smooth, animated responses for better UX

### Authentication & User Management
- **Supabase Authentication**: Secure user authentication with email/password
- **Profile Management**: Update academic information and profile photos
- **Preset Mascots**: Choose from Alma, Roaree, or Millie profile images

## Architecture

### Frontend (React)
- **Framework**: React 19 with React Router for navigation
- **Styling**: Tailwind CSS for modern, responsive design
- **Authentication**: Supabase Auth with protected routes
- **State Management**: React Context API for authentication state
- **Code Splitting**: Lazy loading for optimized performance

### Backend (Flask API)
- **Framework**: Flask with CORS support
- **RAG System**: 
  - Semantic search using pgvector
  - Context retrieval from course bulletins and student reviews
  - LLM-powered answer generation
- **Database**: Supabase (PostgreSQL with pgvector extension)
- **Endpoints**:
  - `/api/chat` - Main chat endpoint
  - `/api/conversations` - Conversation management
  - `/api/profile` - User profile CRUD operations
  - `/api/health` - Health check

## Project Structure

```
ask_alma/
├── frontend/                 # React frontend application
│   ├── public/              # Static assets
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── AskAlma.jsx  # Main chat interface
│   │   │   ├── LandingPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── SignupPage.jsx
│   │   │   └── ProfileModal.jsx
│   │   ├── context/         # React Context (Auth)
│   │   ├── lib/             # Utilities (Supabase client)
│   │   └── constants/       # Configuration constants
│   └── package.json
├── api/                      # Flask backend API
│   └── app.py               # Main Flask application
├── src/
│   ├── embedder/            # RAG system
│   │   ├── rag_query.py     # Query processing
│   │   ├── embedder.py      # Embedding generation
│   │   └── upload_embeddings.py
│   ├── migrations/          # Database migrations
│   └── data_extraction/     # PDF processing
├── requirements.txt          # Python dependencies
└── vercel.json              # Deployment configuration
```

## Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- Supabase account and project
- OpenAI API key

### 1. Frontend Setup

```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend` directory (optional for local development):

```env
REACT_APP_SUPABASE_URL=your_supabase_url
REACT_APP_SUPABASE_ANON_KEY=your_supabase_anon_key
REACT_APP_API_URL=http://localhost:5001
```

### 2. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt
```

Create a `.env` file in `src/embedder/`:

```env
# OpenAI API Key (required for embeddings and LLM)
OPENAI_API_KEY=your_openai_api_key_here

# Supabase/PostgreSQL connection
DATABASE_URL=postgresql://user:password@host:port/database
```

### 3. Database Setup

Run the database migrations in order:

```sql
-- Create user profiles table
\i src/migrations/create_user_profiles.sql

-- Add profile image support
\i src/migrations/add_profile_image.sql

-- Add school column
\i src/migrations/add_profile_school.sql
```

### 4. Data Preparation

The system expects JSONL files with course bulletin data:
- `columbia_college_2024_2025.jsonl`
- `columbia_engineering_2024_2025.jsonl`
- `barnard_2024_2025.jsonl`

Generate embeddings and upload to database:

```bash
# Generate embeddings
cd src/embedder
python embedder.py

# Upload to Supabase
python upload_embeddings.py
```

## Development

### Start Frontend

```bash
cd frontend
npm start
```

The app will be available at `http://localhost:3000`

### Start Backend

```bash
# From project root
python api/app.py
```

The API will be available at `http://localhost:5001`

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run sync-config` - Sync configuration files

## Development Process

This section outlines the process of creating and developing AskAlma from initial concept to production.

### Phase 1: Data Collection & Preparation

The foundation of AskAlma began with gathering and processing academic data:

1. **Course Bulletin/Websites Extraction**
   - Scraped relevant websites, like course bulletins, for Columbia College, Columbia Engineering, and Barnard College
   - Converted information to structured JSONL format
   - Extracted course information, requirements, and academic policies
   - Scripts: `scrape_columbia_college.py`, `scrape_barnard.py`, `scrape_bulletin.py`

3. **Data Chunking**
   - Split large documents into manageable chunks for embedding
   - Optimized chunk size for semantic search effectiveness
   - Preserved context and metadata (source, page numbers, etc.)
   - Scripts: `chunk_scraped_data.py`, `chunk_separate_sources.py`

### Phase 2: RAG System Development

The core retrieval and generation system was built next:

1. **Embedding Generation**
   - Implemented embedding pipeline using OpenAI's `text-embedding-3-small`
   - Created batch processing for efficient embedding generation
   - Stored embeddings with metadata for retrieval
   - Files: `src/embedder/embedder.py`

2. **Vector Database Setup**
   - Set up Supabase PostgreSQL with pgvector extension
   - Created `documents` table with vector indexes for fast similarity search
   - Implemented batch upload system for embeddings
   - Files: `src/embedder/upload_embeddings.py`

3. **Query System**
   - Built semantic search using cosine similarity
   - Implemented context retrieval with top-K matching
   - Integrated LLM (OpenAI GPT) for answer generation
   - Added conversation history support for contextual responses
   - Files: `src/embedder/rag_query.py`

### Phase 3: Backend API Development

The Flask API was developed to connect the frontend to the RAG system:

1. **Core Endpoints**
   - `/api/chat` - Main chat interface with RAG integration
   - `/api/conversations` - Conversation management (list, get, search, delete, rename)
   - `/api/profile` - User profile CRUD operations
   - Files: `api/app.py`

2. **User Profile System**
   - Designed database schema for user profiles
   - Implemented profile-based personalization
   - Added school-specific filtering
   - Created migration scripts for schema evolution
   - Files: `src/migrations/`

3. **Conversation Management**
   - Built conversation storage and retrieval
   - Implemented conversation history for context
   - Added search functionality for conversations
   - Integrated with user authentication

### Phase 4: Frontend Development

The React frontend was built to provide a user-friendly interface:

1. **Initial Setup**
   - Created React app with Create React App
   - Set up routing with React Router
   - Integrated Tailwind CSS for styling
   - Configured Supabase authentication

2. **Core Components**
   - **LandingPage**: Welcome screen with categorized question suggestions
   - **AskAlma**: Main chat interface with conversation management
   - **ProfileModal**: User profile editing with academic information
   - **LoginPage/SignupPage**: Authentication flows
   - **ProtectedRoute**: Route protection for authenticated users

3. **Features Implementation**
   - Real-time chat with typing animations
   - Conversation sidebar with search and management
   - Profile management with preset mascot images
   - Responsive design for mobile and desktop
   - Error handling and loading states

4. **Optimization**
   - Implemented code splitting with React.lazy()
   - Added image optimization and lazy loading
   - Optimized re-renders with React.memo()
   - Improved performance with efficient state management

### Phase 5: Integration & Testing

The final phase involved connecting all components:

1. **API Integration**
   - Connected frontend to Flask API endpoints
   - Implemented error handling and retry logic
   - Added loading states and user feedback
   - Configured CORS for development and production

2. **User Experience Refinement**
   - Added categorized question suggestions
   - Implemented conversation persistence
   - Created smooth animations and transitions
   - Improved error messages and user guidance

3. **Personalization**
   - Integrated user profiles into RAG prompts
   - Implemented school-specific filtering
   - Added course completion tracking
   - Personalized recommendations based on academic context

### Phase 6: Deployment

The project was prepared for production deployment:

1. **Deployment Configuration**
   - Set up Vercel configuration for full-stack deployment
   - Configured environment variables
   - Set up database migrations for production
   - Optimized build process

2. **Production Optimizations**
   - Minified and optimized frontend bundle
   - Configured CDN for static assets
   - Set up serverless functions for API
   - Implemented caching strategies

### Development Workflow

The project followed an iterative development approach:

1. **Backend-First Development**: RAG system and API were built first to establish core functionality
2. **Frontend Integration**: React frontend was developed to consume the API
3. **Feature Iteration**: Features were added incrementally (profiles, conversations, etc.)
4. **User Testing**: Interface and functionality were refined based on usage
5. **Performance Optimization**: Code was optimized for production readiness

## Challenges & Solutions

During development, we encountered several technical challenges.

### 1. Determining Optimal Chunking Size

**Challenge**: Finding the right chunk size for document splitting was crucial for both retrieval accuracy and context preservation. Too small chunks lost important context, while too large chunks reduced semantic search precision.

**Approachs**:
- Experimented with various chunk sizes (200, 500, 1000, 1500 characters)
- Tested retrieval quality with different chunk sizes
- Evaluated how chunk boundaries affected course descriptions and requirements

**Solution**:
- Settled on a balanced chunk size that preserved complete course entries and requirement sections
- Implemented smart chunking that respected document structure (course boundaries, section headers)
- Used overlapping chunks for critical sections to ensure context continuity
- Preserved metadata (source, page numbers) to maintain traceability

### 2. Optimizing Response Time and Speed

**Challenge**: Initial response times were slow due to multiple sequential operations: embedding generation, database queries, and LLM inference. Users experienced delays of 5-10 seconds per query.

**Approaches**:
1. **Database Optimization**:
   - Created IVFFlat indexes on vector embeddings for faster similarity search
   - Optimized SQL queries to reduce database round trips

2. **Context Management**:
   - Limited context retrieval to top-K most relevant chunks (TOP_K = 5)
   - Implemented context truncation (MAX_CONTEXT_CHARS = 8000) to reduce LLM processing time
   - Cached frequently accessed embeddings and metadata

3. **API Optimization**:
   - Implemented batch processing for embedding uploads
   - Added async processing where possible
   - Optimized Flask route handlers to minimize overhead

4. **Frontend Optimizations**:
   - Added loading states and typing animations to improve perceived performance
   - Implemented optimistic UI updates
   - Used React.memo() to prevent unnecessary re-renders

**Solution**: Combined approach reduced average response time from 5-10 seconds to 2-4 seconds, with further improvements through caching and connection pooling.

### 3. Data Collection Challenges

**Challenge**: Collecting and processing academic data from multiple sources presented several obstacles:
- Data quality varied across sources
- Maintaining data freshness as bulletins updated

**Approaches**:
1. **PDF Processing**:
   - Used PDF parsing libraries to extract structured text
   - Handled various PDF formats and layouts
   - Preserved formatting and structure during extraction

2. **Web Scraping**:
   - Handled dynamic content and pagination
   - Built robust error handling for network issues

**Solution**: Built a robust data pipeline with error handling, validation, and incremental update capabilities. The system can now process new bulletins and reviews efficiently while maintaining data quality.

### 4. Personalizing Response Sources to User Profile

**Challenge**: Ensuring that responses were tailored to each user's school, academic year, and completed courses required careful prompt engineering and source filtering. Initial implementation sometimes returned generic or irrelevant information.

**Approaches**:
1. **Profile Integration**:
   - Incorporated user profile information directly into RAG prompts
   - Added explicit instructions to prioritize school-specific sources
   - Implemented course completion tracking to avoid recommending taken courses

2. **Source Filtering**:
   - Created school-specific source patterns for filtering
   - Implemented database-level filtering when possible
   - Added post-retrieval filtering based on user profile

3. **Prompt Engineering**:
   - Designed detailed system prompts that emphasize personalization
   - Added explicit rules about avoiding completed courses
   - Included school-specific terminology and requirements in prompts

4. **Testing & Refinement**:
   - Tested with various profile combinations
   - Verified school-specific responses were accurate
   - Ensured completed courses were properly excluded

**Solution**: Multi-layered approach combining database filtering, prompt engineering, and post-processing ensures responses are highly personalized. The system now:
- Prioritizes information from the user's school (Barnard, Columbia College, SEAS)
- Avoids recommending courses already completed
- Tailors recommendations to academic year and major requirements
- Uses school-specific terminology and requirements

## Deployment

The project is configured for deployment on Vercel:

- **Frontend**: Static build served by Vercel
- **Backend**: Flask API deployed as Vercel serverless functions
- **Database**: Supabase (hosted PostgreSQL)

See `vercel.json` for deployment configuration.

## Configuration

### User Profile Schema

The user profile includes:
- `user_id` (UUID) - Supabase user ID
- `school` - One of: `columbia_college`, `columbia_engineering`, `barnard`
- `academic_year` - One of: `first-year`, `sophomore`, `junior`, `senior`, `graduate`, `other`
- `major` - Free text
- `minors` - Array of strings
- `classes_taken` - Array of course codes (e.g., `["COMS 3134", "ECON 1105"]`)
- `profile_image` - Base64 data URL or preset image path

### RAG Configuration

In `src/embedder/rag_query.py`:
- `TOP_K = 5` - Number of relevant chunks to retrieve
- `MAX_CONTEXT_CHARS = 8000` - Maximum context length
- `GEN_MODEL = "openai:gpt-4o-mini"` - LLM model for generation

## API Endpoints

### Chat
```
POST /api/chat
Body: {
  "question": "What are the core classes?",
  "conversation_id": "uuid" (optional),
  "user_id": "uuid" (optional)
}
```

### Conversations
```
GET /api/conversations?user_id=uuid
GET /api/conversations/<id>
GET /api/conversations/search?user_id=uuid&query=search_term
PATCH /api/conversations/<id>  # Rename conversation
DELETE /api/conversations/<id>
```

### Profile
```
GET /api/profile/<user_id>
POST /api/profile  # Create or update
```

## Tech Stack

### Frontend
- React 19
- React Router 7
- Tailwind CSS
- Supabase JS Client
- Lucide React (icons)

### Backend
- Flask
- Flask-CORS
- OpenAI API
- LangChain
- psycopg2 (PostgreSQL)
- Supabase (PostgreSQL with pgvector)

## License

This project is for educational purposes.
