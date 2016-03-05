import copy
import os
import re
from time import localtime, strftime

import git
import jinja2
import yaml


YAML_DIR = "yaml"
BUILD_DIR = "build"
TEMPLATES_DIR = "templates"
SECTIONS_DIR = "sections"
DEFAULT_SECTION = "items"
OUTPUT_DIR = "output"
LETTERS_DIR = "with_letters"
BASE_FILE_NAME = "resume"
LETTER_FILE_NAME = "letter_body"
YAML_STYLE = "style"
YAML_MAIN = "resume"
YAML_BUSINESSES = "businesses"
YAML_PUBLICATIONS = "publications"
DATE_FMT = "%Y--%m--%d"

os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, LETTERS_DIR), exist_ok=True)

last_updated = localtime(git.Repo().head.commit.committed_date)
last_updated_string = strftime(DATE_FMT, last_updated)


class RenderContext(object):
    def __init__(self, context_name, filetype, jinja_options, replacements):
        self.filetype = filetype
        self.replacements = replacements

        context_templates_dir = os.path.join(TEMPLATES_DIR, context_name)

        self.base_template = BASE_FILE_NAME + self.filetype
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

    def _render_template(self, template_name, data):
        return self.jinja_env.get_template(template_name).render(**data)

    @staticmethod
    def _make_double_list(items):
        double_list = [{"first": items[i * 2], "second": items[i * 2 + 1]}
                       for i in range(len(items) // 2)]
        if len(items) % 2:
            double_list.append({"first": items[-1]})
        return double_list

    def render(self, data):
        data = self.make_replacements(data)
        self._name = data["name"]["abbrev"]

        body = ""
        for section_data in data["sections"]:
            if self.context_type_name in section_data:
                section_type = section_data[self.context_type_name]
            elif "type" in section_data:
                section_type = section_data["type"]
            else:
                section_type = DEFAULT_SECTION

            if section_type == "doubleitems":
                section_data["items"] = self._make_double_list(
                    section_data["items"])

            section_template_name = os.path.join(
                SECTIONS_DIR, section_type + self.filetype
            )

            rendered_section = self._render_template(
                section_template_name, section_data
            )
            body += rendered_section.rstrip() + "\n\n\n"

        data["body"] = body
        data["updated"] = last_updated_string

        return self._render_template(self.base_template, data).rstrip() + "\n"

    def write(self, output_data, base=BASE_FILE_NAME):
        output_file = os.path.join(
            BUILD_DIR, "{name}_{base}{ext}".format(name=self._name,
                                                   base=base,
                                                   ext=self.filetype)
        )
        with open(output_file, "w") as fout:
            fout.write(output_data)


LATEX_CONTEXT = RenderContext(
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


latex = jinja2.Environment(
    block_start_string='~<',
    block_end_string='>~',
    variable_start_string='<<',
    variable_end_string='>>',
    comment_start_string='<#',
    comment_end_string='#>',
    trim_blocks=True,
    lstrip_blocks=True,
    loader=jinja2.FileSystemLoader(os.path.abspath('.')),
)


def process_resume(context, data, base=BASE_FILE_NAME):
    rendered_resume = context.render(data)
    context.write(rendered_resume, base=base)


def main2():
    with open(os.path.join(YAML_DIR, YAML_MAIN + ".yaml")) as resume_data:
        yaml_data = yaml.load(resume_data)
    with open(os.path.join(YAML_DIR, YAML_STYLE + ".yaml")) as style_data:
        yaml_data.update(**yaml.load(style_data))
    with open(os.path.join(YAML_DIR,
                           YAML_BUSINESSES + ".yaml")) as businesses_data:
        businesses = yaml.load(businesses_data)

    process_resume(LATEX_CONTEXT, yaml_data)

    body_template = latex.get_template("templates/latex/letter_body.tex")
    for business in businesses:
        data = {k: v for d in (yaml_data, businesses[business])
                for k, v in d.items()}
        body = body_template.render(**data)
        data["business"]["body"] = body
        process_resume(LATEX_CONTEXT, data, base=business)


def main():
    main_template = latex.get_template("templates/latex/resume.tex")
    body_template = latex.get_template("templates/latex/letter_body.tex")

    with open("{}/{}.yaml".format(YAML_DIR,
                                  YAML_STYLE)) as style_data:
        style = yaml.load(style_data)

    with open("{}/{}.yaml".format(YAML_DIR,
                                  YAML_MAIN)) as resume_data:
        data = yaml.load(resume_data)
    file_root = data["name"]["abbrev"]
    data["updated"] = last_updated_string

    with open("{}/{}.yaml".format(YAML_DIR,
                                  YAML_BUSINESSES)) as businesses_data:
        businesses = yaml.load(businesses_data)

    for business in businesses:
        body = body_template.render(**data, **businesses[business])
        businesses[business]["body"] = body
        with open("{}/{}_{}.tex".format(BUILD_DIR, file_root, business),
                  "w") as resume:
            resume.write(main_template.render(
                **style,
                **data,
                business=businesses[business],
            ))

    with open("{}/{}_resume.tex".format(BUILD_DIR, file_root), "w") as resume:
        resume.write(main_template.render(
            **style,
            **data,
        ))


if __name__ == '__main__':
    main2()
