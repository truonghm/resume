CONTEXTS = {
    "html": dict(
        context_name="html",
        filetype=".html",
        jinja_options=dict(
            trim_blocks=True,
            lstrip_blocks=True,
        ),
        replacements={
            r"\\ ": "&nbsp;",                              # spaces
            r"\\textbf{([^}]*)}": r"<strong>\1</strong>",  # bold
            r"\\textit{([^}]*)}": r"<em>\1</em>",          # italic
            r"\\LaTeX": "LaTeX",                           # \LaTeX
            r"\\TeX": "TeX",                               # \TeX
            "---": "&mdash;",                              # em dash
            "--": "&ndash;",                               # en dash
            r'``([^\']*)\'\'': r'"\1"',                    # quotes
            r"\\%": "%",                                   # percent
        }
    ),

    "latex": dict(
        context_name="latex",
        filetype=".tex",
        output_filetype=".pdf",
        jinja_options=dict(
            block_start_string="~<",
            block_end_string=">~",
            variable_start_string="<<",
            variable_end_string=">>",
            comment_start_string="<#",
            comment_end_string="#>",
            trim_blocks=True,
            lstrip_blocks=True,
        ),
        replacements={}
    ),

    "markdown": dict(
        context_name="markdown",
        filetype=".md",
        jinja_options=dict(
            trim_blocks=True,
            lstrip_blocks=True,
        ),
        replacements={
            r"\\ ": " ",                      # spaces
            r"\\textbf{([^}]*)}": r"**\1**",  # bold text
            r"\\textit{([^}]*)}": r"*\1*",    # italic text
            r"\\LaTeX": "LaTeX",              # \LaTeX
            r"\\TeX": "TeX",                  # \TeX
            "---": "-",                       # em dash
            "--": "-",                        # en dash
            r'``([^\']*)\'\'': r'"\1"',       # quotes
            r"\\%": "%" ,                     # percent
        }
    ),

    "plaintext": dict(
        context_name="plaintext",
        filetype=".txt",
        jinja_options=dict(
            trim_blocks=True,
            lstrip_blocks=True,
        ),
        replacements={
            r"\\ ": " ",                      # spaces
            r"\\textbf{([^}]*)}": r"**\1**",  # bold text
            r"\\textit{([^}]*)}": r"*\1*",    # italic text
            r"\\LaTeX": "LaTeX",              # \LaTeX
            r"\\TeX": "TeX",                  # \TeX
            "---": "-",                       # em dash
            "--": "-",                        # en dash
            r'``([^\']*)\'\'': r'"\1"',       # quotes
            r"\\%": "%" ,                     # percent
        }
    ),
}

