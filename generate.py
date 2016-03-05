import copy
import os
import re
from time import localtime, strftime

import git
import jinja2
import yaml


with open("config.yaml") as configuration_file:
    config = yaml.load(configuration_file)
os.makedirs(config["BUILD_DIR"], exist_ok=True)
os.makedirs(os.path.join(config["OUTPUT_DIR"],
                         config["LETTERS_DIR"]), exist_ok=True)

last_updated = localtime(git.Repo().head.commit.committed_date)
last_updated_string = strftime(config["DATE_FMT"], last_updated)


def main():
    with open(os.path.join(config["YAML_DIR"],
                           config["YAML_MAIN"] + ".yaml")) as resume_data:
        yaml_data = yaml.load(resume_data)
    with open(os.path.join(config["YAML_DIR"],
                           config["YAML_STYLE"] + ".yaml")) as style_data:
        yaml_data.update(**yaml.load(style_data))
    with open(
        os.path.join(config["YAML_DIR"], config["YAML_BUSINESSES"] + ".yaml")
    ) as business_data:
        businesses = yaml.load(business_data)

    for section in yaml_data["sections"]:
        if ("type" in section
                and section["type"] == "publications"
                and "items" not in section):
            with open(
                os.path.join(config["YAML_DIR"],
                             config["YAML_PUBLICATIONS"] + ".yaml")
            ) as pub_data:
                pubs = yaml.load(pub_data)
            if not pubs:
                yaml_data["sections"].remove(section)
            else:
                section["items"] = pubs
            break

    process_resume(LATEX_CONTEXT, yaml_data)

    for business in businesses:
        data = {k: v for d in (yaml_data, businesses[business])
                for k, v in d.items()}
        data["business"]["body"] = LATEX_CONTEXT.render_template(
            config["LETTER_FILE_NAME"], data
        )
        process_resume(LATEX_CONTEXT, data, base=business)


def process_resume(context, data, base=config["BASE_FILE_NAME"]):
    rendered_resume = context.render(data)
    context.write(rendered_resume, base=base)


class ContextRenderer(object):
    def __init__(self, context_name, filetype, jinja_options, replacements):
        self.filetype = filetype
        self.replacements = replacements

        context_templates_dir = os.path.join(config["TEMPLATES_DIR"],
                                             context_name)

        self.base_template = config["BASE_FILE_NAME"]
        self.context_type_name = context_name + "type"

        self.jinja_options = jinja_options.copy()
        self.jinja_options["loader"] = jinja2.FileSystemLoader(
            searchpath=context_templates_dir
        )
        self.jinja_options["undefined"] = jinja2.StrictUndefined
        self.jinja_env = jinja2.Environment(**self.jinja_options)

    def make_replacements(self, data):
        data = copy.copy(data)

        if isinstance(data, str):
            for o, r in self.replacements:
                data = re.sub(o, r, data)

        elif isinstance(data, dict):
            for k, v in data.items():
                data[k] = self.make_replacements(v)

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                data[idx] = self.make_replacements(item)

        return data

    def render_template(self, template_name, data):
        full_name = template_name + self.filetype
        return self.jinja_env.get_template(full_name).render(**data)

    @staticmethod
    def _make_double_list(items):
        double_list = [{"first": items[i * 2], "second": items[i * 2 + 1]}
                       for i in range(len(items) // 2)]
        if len(items) % 2:
            double_list.append({"first": items[-1]})
        return double_list

    # noinspection PyTypeChecker
    def render(self, data):
        data = self.make_replacements(data)
        self._name = data["name"]["abbrev"]

        body = ""
        for section_data in data["sections"]:
            section_data["theme"] = data["theme"]

            if self.context_type_name in section_data:
                section_type = section_data[self.context_type_name]
            elif "type" in section_data:
                section_type = section_data["type"]
            else:
                section_type = config["DEFAULT_SECTION"]

            if section_type == "doubleitems":
                section_data["items"] = self._make_double_list(
                    section_data["items"])

            section_template_name = os.path.join(
                config["SECTIONS_DIR"], section_type
            )

            rendered_section = self.render_template(
                section_template_name, section_data
            )
            body += rendered_section.rstrip() + "\n\n\n"

        data["body"] = body
        data["updated"] = last_updated_string

        return self.render_template(self.base_template, data).rstrip() + "\n"

    def write(self, output_data, base=config["BASE_FILE_NAME"]):
        output_file = os.path.join(
            config["BUILD_DIR"], "{name}_{base}{ext}".format(name=self._name,
                                                             base=base,
                                                             ext=self.filetype)
        )
        with open(output_file, "w") as fout:
            fout.write(output_data)


LATEX_CONTEXT = ContextRenderer(
    "latex",
    ".tex",
    dict(
        block_start_string='~<',
        block_end_string='>~',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
        trim_blocks=True,
        lstrip_blocks=True,
    ),
    []
)


MARKDOWN_CONTEXT = ContextRenderer(
    'markdown',
    '.md',
    dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    [
        (r'\\ ', ' '),                      # spaces
        (r'\\textbf{([^}]*)}', r'**\1**'),  # bold text
        (r'\\textit{([^}]*)}', r'*\1*'),    # italic text
        (r'\\LaTeX', 'LaTeX'),              # \LaTeX to boring old LaTeX
        (r'\\TeX', 'TeX'),                  # \TeX to boring old TeX
        ('---', '-'),                       # em dash
        ('--', '-'),                        # en dash
        (r'``([^\']*)\'\'', r'"\1"'),       # quotes
    ]
)


HTML_CONTEXT = ContextRenderer(
    'html',
    '.html',
    dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    [
        (r'\\ ', '&nbsp;'),                              # spaces
        (r'\\textbf{([^}]*)}', r'<strong>\1</strong>'),  # bold
        (r'\\textit{([^}]*)}', r'<em>\1</em>'),          # italic
        (r'\\LaTeX', 'LaTeX'),                           # \LaTeX
        (r'\\TeX', 'TeX'),                               # \TeX
        ('---', '&mdash;'),                              # em dash
        ('--', '&ndash;'),                               # en dash
        (r'``([^\']*)\'\'', r'"\1"'),                    # quotes
    ]
)


if __name__ == '__main__':
    main()
