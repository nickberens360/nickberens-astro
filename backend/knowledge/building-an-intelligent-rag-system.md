---
title: "Building an Intelligent RAG System: From Manual Configuration to LLM-Powered Intelligence"
description: "A deep dive into the evolution of my personal website's AI assistant, showcasing the journey from manual data management to a fully automated, LLM-powered Retrieval-Augmented Generation system."
pubDate: 2025-08-15
heroImage: "/blog-placeholder-3.jpg"
author: "Probably AI"
backgroundColor: "#b8ffe9"
theme: "light"
aiPrompt: "Please write a blog post about the development process to get the AI 
RAG system running. Use the git commits as a reference to decide on what to 
write. Output to a markdown file with the name of your choosing to the content/blog dir."
---

I've always been curious about AI, but reading papers and tutorials only gets you so far. I wanted to really understand how these systems work - not just in theory, but by building something real. Something that could solve an actual problem. So when I noticed I was repeatedly answering similar questions about my work experience ("What frameworks do you use?" "Tell me about your Vue projects"), it clicked: why not build an AI assistant that could handle these conversations for me?

What started as a learning exercise quickly spiraled into a months-long deep dive into RAG systems. When I began, those three letters meant nothing to me. Now? Well, let me share what I discovered.

## How This All Started (Spoiler: It Was Messy)

Picture this: March, rainy Sunday, me at my desk with a fresh cup of coffee and absolutely no idea what I was getting into. My plan seemed straightforward - take some JSON files with my background info, feed them to a language model, and boom: instant AI assistant.

The reality? Not quite that simple.

## The "Simple" Beginning That Wasn't

My first prototype was spectacular in its failure. Ask "What programming languages do you know?" and you might hear about my hiking habits or my dog Charlie. The system had all the contextual awareness of a magic 8-ball - technically providing answers, just not to the questions being asked.

## Why FastAPI (And My Brief Flirtation with Flask)

Flask seemed like the obvious choice initially. Everyone uses Flask, right? But after wrestling with async database calls for two frustrating hours, I made the switch to FastAPI. The decision paid off immediately - automatic API documentation, better async support, and cleaner code structure. Sometimes the popular choice isn't the right choice.

## ChromaDB: The Vector Store That Actually Worked

Here's a confession: I burned three days trying to configure Pinecone before realizing ChromaDB could run locally and do everything I needed. No cloud setup, no API keys to manage, no distributed systems headaches. Just a vector store that worked out of the box. Sometimes the simplest solution is the best one.

## The Great LLM Shopping Experience

After some experimentation (and budget considerations), Google's Gemini models became my workhorses. The text-embedding-004 model handles semantic understanding beautifully, while the generation model crafts responses that sound reasonably human. The balance between cost and quality made it perfect for a personal project.

## The YAML Nightmare (Or: How I Learned to Hate Configuration Files)

This phase taught me humility. My "brilliant" idea involved manually defining every piece of content in YAML files. Adding a new project meant updating multiple configs. Mapping relationships between "frontend work" and "Vue development"? More manual configuration.

```yaml
retrievers:
  - name: "experience_retriever"
    description: "Professional experience and work history"
    data_source: "resume.json"
    content_type: "experience"
    keywords: ["work", "job", "experience", "employment"]
    # Yes, I actually maintained keyword lists like this
```

The approach was fundamentally flawed. I was trying to anticipate every possible way someone might phrase a question. The maintenance burden grew exponentially with each new piece of content. The keyword matching produced comically bad results - somehow "Vue" triggered responses about hiking.

## The "Aha!" Moment (At 2 AM, Naturally)

Tuesday, 2 AM, debugging session number three. I'm staring at 500+ lines of keyword matching logic when the obvious finally hits me: I'm using artificial intelligence while trying to manually program intelligence. The irony was almost painful.

Why was I writing elaborate if-else chains when I had access to models that understand language naturally?

## Letting the AI Do the AI Things

The transformation was dramatic:

```python
# My old approach (the path of suffering):
if "experience" in query.lower() or "work" in query.lower():
    content_type = "experience"
elif "vue" in query.lower() or "frontend" in query.lower():
    content_type = "frontend"
# ... 200 more lines of this nonsense

# The new way (why didn't I do this from the start?):
analysis = await llm.analyze_query_intent(query)
# Let the AI figure out what the human actually wants
```

Suddenly, the system understood that "What frontend stuff have you worked on?" and "Tell me about your Vue experience" were related queries. No manual mapping required.

## The Magic Folder (Finally, Something That Just Works)

Remember those three config files per content update? I built what I now call my "magic folder" - drop files into `backend/knowledge/` and the system handles the rest. Markdown, JSON, even PDFs (though early PDF parsing had some amusing failures - apparently my resume was about cooking recipes).

The beauty lies in the simplicity. Save a new project writeup, and the AI immediately knows about it. No configuration, no manual indexing, just automatic content discovery.

## LLM-Powered Document Tagging

During indexing, the system uses AI to understand content semantically:

```python
async def tag_document_with_llm(self, content: str) -> List[str]:
    """Use LLM to extract semantic topics from content"""
    prompt = f"""
    Analyze this content and extract 3-5 semantic topics that best describe it.
    Focus on: technical skills, job roles, company names, project types, technologies.
    
    Content: {content[:500]}...
    
    Return topics as a comma-separated list.
    """
    
    response = await self.indexing_llm.ainvoke(prompt)
    return [topic.strip() for topic in response.content.split(',')]
```

## Intelligent Document Re-ranking

After initial retrieval, another AI pass ensures the most relevant documents surface:

```python
async def rerank_documents_with_llm(self, query: str, documents: List[Document]) -> List[Document]:
    """Use LLM to re-rank documents by relevance to query"""
    
    for i, doc in enumerate(documents):
        score_prompt = f"""
        Rate how relevant this document is to the query on a scale of 1-10.
        Query: {query}
        Document: {doc.page_content[:300]}...
        
        Return only a number from 1-10.
        """
        
        response = await self.llm.ainvoke(score_prompt)
        # Parse score and update document metadata
```

## When My AWS Bill Made Me Cry

A month in, reality hit hard. My weekend of enthusiastic testing generated a $200 bill. For a personal project, that wasn't sustainable. Time to get smart about model usage.

## The Great Model Optimization (Or: How I Learned to Love Cheap Models)

The solution was obvious once I thought about it: not every task needs the most powerful model. I started using Claude Haiku (fast, cheap) for background tasks like content indexing, reserving Claude Sonnet (powerful, expensive) for actual user interactions.

Result? 70% cost reduction with zero impact on user experience. Sometimes optimization is just about using the right tool for each job.

## Async Performance Optimization

Moving LLM calls to a thread pool prevented blocking:

```python
async def tag_document_with_llm_async(self, content: str) -> List[str]:
    """Offload LLM calls to thread pool for better async performance"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        self.thread_pool_executor,
        self._tag_document_sync,
        content
    )
```

## Intelligent Caching

Multiple caching layers keep things fast and affordable:

- Vector store caching - Skip re-indexing unchanged files
- Query result caching - Instant responses for repeated questions
- LLM response caching - Reduce API costs for similar queries

## Phase 5: Advanced Features

### Query Logging and Analytics

The system tracks everything (privacy-consciously):
- User queries and response quality
- Geographic patterns (GDPR-compliant)
- System performance metrics
- Popular topics and trends

The admin dashboard reveals fascinating patterns in how people interact with the assistant.

### Security and Privacy

Security wasn't an afterthought:
- Input sanitization prevents injection attacks
- Rate limiting manages both abuse and costs
- Privacy-first logging with hashed IPs
- GDPR compliance with proper consent management

### Illustration Search

The system can even search through my design portfolio intelligently:

```python
async def search_illustrations(self, query: str) -> List[Dict]:
    """Search illustrations using semantic similarity and metadata"""
    
    # Vectorize the query
    query_embedding = await self.embeddings.aembed_query(query)
    
    # Search with metadata filtering
    results = await self.vector_store.asimilarity_search_by_vector(
        query_embedding,
        k=5,
        filter={"content_type": "illustration"}
    )
    
    return self._format_illustration_results(results)
```

## Technical Challenges and Solutions

### Error Handling and Resilience

Production systems need to handle failures gracefully:

```python
async def robust_llm_call(self, prompt: str, max_retries: int = 3) -> str:
    """Make LLM calls with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            response = await self.llm.ainvoke(prompt)
            return self._validate_response(response)
        except (RateLimitError, APIError) as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Type Safety with MyPy

Maintaining type safety across async operations required discipline:

```python
from typing import List, Dict, Optional, Union, AsyncGenerator

async def process_documents(
    self, 
    files: List[str]
) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
    """Type-safe async generator for document processing"""
    for file_path in files:
        try:
            metadata = await self._extract_metadata(file_path)
            yield file_path, metadata
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue
```

## The Results: A Truly Intelligent System

The evolution from manual configuration to AI-powered intelligence delivered:

### Zero Configuration
- Drop files in the knowledge directory
- Automatic content discovery and indexing
- Intelligent categorization without human input

### Superior Accuracy
- Natural language understanding
- Context-aware document ranking
- Multi-layered relevance scoring

### Outstanding Performance
- Sub-second response times
- Efficient caching reduces costs
- Async architecture handles concurrent users

### Rich Analytics
- Detailed query and performance logging
- Geographic usage patterns
- System health monitoring

## What I Wish I'd Known From the Start

**Don't Fight the LLM, Work With It**
I wasted weeks trying to outsmart AI with clever algorithms. The breakthrough came when I started treating LLMs as reasoning partners, not fancy search engines.

**Your First Version Will Be Terrible, and That's Fine**
My initial system was embarrassingly bad. But it worked just enough to teach me what was possible. Sometimes you need to build the wrong thing to understand what the right thing looks like.

**Monitoring is Boring But Essential**
Adding logging felt like busywork until I spent two weeks debugging performance issues that proper monitoring would have revealed in minutes. Add telemetry early - future you will be grateful.

**Users Will Break Your System in Creative Ways**
Someone asked my assistant "How many pancakes can Nick eat?" and it spent ten minutes searching my professional portfolio for dietary preferences. Users are wonderfully unpredictable - design for chaos.

## What's Next? (My Ever-Growing Todo List)

The dangerous thing about working systems is they inspire endless feature ideas:

- **Image understanding** - For when someone inevitably uploads a screenshot
- **Conversation memory** - So the AI remembers context between sessions
- **Learning from feedback** - Currently mistakes just frustrate me; soon they'll improve the system
- **Better analytics** - Understanding what people actually ask helps improve content

## For Other Developers Thinking About This

Some honest advice from the trenches:

Start embarrassingly simple. My first version was basically a glorified grep over JSON files. It was terrible, but it worked, and working beats perfect every single time.

Don't try to solve every problem immediately. This system went through four major rewrites before reaching something I was proud of. Each iteration taught valuable lessons about what users actually need versus what I thought they needed.

Add monitoring from day one. Nothing worse than debugging production issues blind at 3 AM because you thought logging was optional.

## The Real Lesson Here

Building this RAG system taught me that great AI projects aren't about using the fanciest models or most complex architectures. They're about solving real problems in ways that actually work.

My AI assistant might not win any Turing tests, but it handles repetitive questions about my background so I don't have to. That's exactly what I set out to build - and along the way, I gained a deep understanding of how these AI systems really work.

The future of AI isn't just about building smarter systems - it's about building systems that make our daily work a little easier, one practical solution at a time.

*Interested in the technical details? The complete source code and documentation for this RAG system is available in my personal website repository. Feel free to explore, learn, and adapt these patterns for your own projects.*