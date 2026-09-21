from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    level: int
    category: str = ""


@dataclass(frozen=True)
class Milestone:
    when: str
    title: str
    detail: str
    icon: str = "•"


@dataclass(frozen=True)
class Certificate:
    title: str
    issuer: str
    when: str
    url: str = ""


@dataclass(frozen=True)
class Identity:
    name: str
    class_name: str
    title: str
    status: str
    taglines: tuple[str, ...]
    role: str
    education: str
    stack: tuple[str, ...]
    currently: str
    next_up: str
    open_to: tuple[str, ...]
    cta_title: str
    cta_text: str
    skills: tuple[Skill, ...] = ()
    timeline: tuple[Milestone, ...] = ()
    certificates: tuple[Certificate, ...] = ()


IDENTITY = Identity(
    name="Suyash Singh",
    class_name="Suyash",
    title="Product-minded Developer",
    status="Building and sharing work in public",
    taglines=(
        "B.Tech CSE Student",
        "Python • C • Git & GitHub",
        "Learning & Building in Public",
        "More Projects Coming Soon",
    ),
    role="Product-minded developer",
    education="B.Tech CSE",
    stack=("Python", "C", "Git", "GitHub"),
    currently="Learning & building in public",
    next_up="More projects coming soon",
    open_to=("Thoughtful teams", "Ambitious products", "Useful engineering work"),
    cta_title="Let's talk about the next build",
    cta_text="Open to thoughtful teams, ambitious products, and useful engineering work.",
    # Edit these three lists to fit your own stack, story and certificates.
    skills=(
        Skill("Python", 85, "Languages"),
        Skill("C", 65, "Languages"),
        Skill("JavaScript", 55, "Languages"),
        Skill("Git & GitHub", 80, "Tools"),
        Skill("Linux / CLI", 70, "Tools"),
        Skill("SQL", 50, "Tools"),
    ),
    timeline=(
        Milestone("2026", "B.Tech CSE • First Year", "Started my degree and built a strong foundation in CS fundamentals.", "🎓"),
        Milestone("2027", "Second Year • Skill Growth", "Explored coding, problem solving, and hands-on project work.", "🚀"),
        Milestone("2028", "Third Year • Building in Public", "Began shipping projects, learning by doing, and documenting progress.", "✨"),
        Milestone("2029", "Fourth Year • Real Projects", "Focused on meaningful builds, polishing skills, and solving practical problems.", "🛠️"),
        Milestone("2030", "Next Chapter", "Preparing for ambitious product work and the next big build.", "🎯"),
    ),
    certificates=(
        Certificate("Certificates coming soon", "B.Tech CSE", "2026"),
    ),
)
