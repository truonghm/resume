#!/usr/bin/env python3
"""
Generates LaTeX, Markdown, and HTML copies of my résumé.

More information is available in the README file.

"""
from resume_generator import environment_setup, ResumeGenerator


def main():
    """
    Main hook for script.

    """
    environment_setup()
    ResumeGenerator().run(context_names=[
        "latex",
        "plaintext",
    ])


if __name__ == "__main__":
    main()
