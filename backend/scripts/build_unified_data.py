import json
from pathlib import Path

def build_unified_data():
    """
    Builds a single, structured JSON data file from various sources.
    This file acts as the "source of truth" for the RAG system, enabling
    logical chunking and rich metadata embedding.
    """
    base_path = Path("public")
    output_path = base_path / "unified_data.json"

    # --- Illustrations JSON (already structured) ---
    illustrations_path = base_path / "illustrations.json"
    if illustrations_path.exists():
        with open(illustrations_path, "r", encoding="utf-8") as f:
            illustrations_data = json.load(f)
    else:
        illustrations_data = []
        print(f"⚠️ Illustrations file not found at {illustrations_path}")

    # --- Manually Structured Resume Data ---
    # This manual structuring is the key to high-quality retrieval.
    # It replaces unreliable PDF parsing with clean, logical sections.
    resume_data = {
        "summary": "Passionate problem solver and lifelong learner with 10+ years’ experience developing and designing maintainable and scalable frontends.",
        "skills": [
            {"name": "Vue.js", "category": "Frontend Frameworks"},
            {"name": "Nuxt.js", "category": "Frontend Frameworks"},
            {"name": "Vuetify.js", "category": "UI Libraries"},
            {"name": "Vuex/Pinia", "category": "State Management"},
            {"name": "Vue Router", "category": "Routing"},
            {"name": "JavaScript", "category": "Languages"},
            {"name": "CSS/Scss", "category": "Styling"},
            {"name": "Responsive CSS Design", "category": "Styling"},
            {"name": "WordPress", "category": "CMS"},
            {"name": "Prismic.io CMS", "category": "CMS"},
            {"name": "GIT", "category": "Version Control"},
            {"name": "Agile Development", "category": "Methodologies"},
            {"name": "Netlify", "category": "Deployment"},
            {"name": "Chart.js", "category": "Data Visualization"},
            {"name": "IntelliJ IDEA", "category": "Software Tools"},
            {"name": "Adobe Photoshop", "category": "Software Tools"},
            {"name": "Adobe XD", "category": "Software Tools"},
            {"name": "Sketch", "category": "Software Tools"},
            {"name": "Atlassian Software", "category": "Software Tools"}
        ],
        "experience": [
            {
                "company": "Hillman Group, Robotics & Digital Solutions",
                "role": "Frontend Developer",
                "dates": "10/2021 – 3/2025",
                "location": "Boulder, CO",
                "points": [
                    "Led successful migration of enterprise CRM dashboard from Vue/Vuetify 2 to 3, modernizing codebase and improving application maintainability.",
                    "Built headless CMS marketing solutions using Vue/Nuxt, integrating Prismic.io APIs to enable dynamic content management.",
                    "Engineered custom component documentation plugin, streamlining development workflows and fostering collaborative knowledge sharing across teams.",
                    "Built Axios caching layer for efficient data management, boosting CRM responsiveness and streamlining user workflow.",
                    "Facilitated UX research sessions with stakeholders using card sorting methods to optimize navigation structure and information architecture.",
                    "Led an initiative to integrate Cypress into our workflow to ensure feature integrity through end-to-end testing.",
                    "Led product feature design initiatives using Adobe XD, reducing workload for the design team when needed.",
                    "Actively contributed to daily standups, sprint planning and retrospectives to ensure project alignment and continuous improvement."
                ]
            },
            {
                "company": "Wisnet.com LLC",
                "role": "Frontend Developer",
                "dates": "8/2012 – 10/2021",
                "location": "Fond Du Lac, WI",
                "points": [
                    "Developed Vue.js interfaces integrated with Laravel and WordPress APIs, focusing on scalability and maintainability.",
                    "Created component library documentation with Storybook.js to improve team development efficiency.",
                    "Built headless WordPress sites using Nuxt.js and Netlify for improved performance.",
                    "Set up automated deployments to Netlify and Cloudflare Pages.",
                    "Developed over 100 custom WordPress themes for diverse client needs.",
                    "Maintained 200+ WordPress sites across WP Engine and Kinsta platforms."
                ]
            },
            {
                "company": "Thrivent Financial",
                "role": "Frontend Developer Intern",
                "dates": "6/2012 – 8/2012",
                "location": "Appleton, WI",
                "points": [
                    "Wrote semantic HTML and scalable CSS per issue requests at Thrivent Financial."
                ]
            }
        ],
        "education": [
            {
                "institution": "Fox Valley Technical College",
                "degree": "Associate of Applied Science: Web Design and Development",
                "dates": "Aug 2008 – Jun 2012",
                "location": "Appleton, WI",
                "notes": "Graduated with honors, 3.89 GPA."
            }
        ],
        "accomplishments": [
            {
                "title": "Atomic Docs",
                "description": "Developed an open-source tool for creating and managing Scss components called Atomic Docs with 781 stars on GitHub.",
                "link": "http://atomicdocs.io/"
            },
            {
                "title": "CSS-Tricks Article",
                "description": "Authored an article for css-tricks.com discussing style guide driven development.",
                "link": "https://css-tricks.com/style-guide-driven-development-atomic-docs/"
            }
        ]
    }

    # --- Manually Structured About Data ---
    about_data = {
        "introduction": "Nick Berens is a passionate frontend developer with a strong focus on creating elegant, responsive, and accessible user interfaces. His work demonstrates a deep understanding of modern web technologies and a commitment to clean, maintainable code.",
        "sections": [
            {
                "heading": "Illustration Work",
                "content": "Nick is a talented illustrator who creates unique character designs and visual elements. His illustration portfolio includes a diverse range of characters and styles, such as 'Kinda Dumb Doug', animal-themed artwork, and playful concepts like 'Pool Shark'. His illustrations showcase a distinctive style that combines humor, creativity, and technical skill."
            },
            {
                "heading": "Frontend Styleguide Development",
                "content": "Nick has developed a comprehensive CSS framework and design system. His approach includes a well-structured CSS architecture, responsive design utilities, extensive utility classes, consistent naming conventions, and fluid typography. His styleguide shows a methodical approach to frontend development, creating systems that are both flexible and consistent."
            },
            {
                "heading": "AI & Backend Development",
                "content": "Nick is actively developing skills in AI and backend development. This includes experience with building AI-powered applications using LangChain, implementing retrieval-augmented generation (RAG) systems, creating robust backends with FastAPI, and working with vector databases."
            },
            {
                "heading": "Technology Stack",
                "content": "Nick's technical expertise spans multiple technologies: Frontend (Vue.js, Astro, HTML, CSS, JavaScript), Backend (Python, FastAPI), AI/ML (LangChain, Google Generative AI, Anthropic Claude), Design (Illustration, UI/UX, Design Systems), and Tools (Git, npm)."
            },
            {
                "heading": "Personal Touch",
                "content": "Nick combines technical expertise with creative vision, allowing him to bridge the gap between design and development. His work reflects a commitment to both aesthetic quality and technical excellence, creating digital experiences that are both beautiful and functional."
            }
        ]
    }

    # --- Build unified structure ---
    unified_data = {
        "resume": resume_data,
        "about": about_data,
        "illustrations": illustrations_data
    }

    # --- Write output ---
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unified_data, f, indent=2)
        print(f"✅ Structured unified data file created at {output_path}")
    except (IOError, OSError) as e:
        print(f"❌ Failed to write unified data file: {e}")
        raise

    print(f"✅ Structured unified data file created at {output_path}")

if __name__ == "__main__":
    build_unified_data()