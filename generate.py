import copy
import glob
import hashlib
import os
import re
import shutil
import subprocess
import time

import git
import jinja2
import tqdm
import yaml


last_updated = time.localtime(git.Repo().head.commit.committed_date)
with open("config.yaml") as config_file:
    config = yaml.load(config_file)
config["updated"] = time.strftime(config["DATE_FMT"], last_updated)


def main():
    os.makedirs(config["BUILD_DIR"], exist_ok=True)
    os.makedirs(os.path.join(config["OUTPUT_DIR"], config["LETTERS_DIR"]),
                exist_ok=True)

    with open(os.path.join(config["YAML_DIR"],
                           config["YAML_MAIN"] + ".yaml")) as resume_data:
        data = yaml.load(resume_data)
    with open(
        os.path.join(config["YAML_DIR"], config["YAML_BUSINESSES"] + ".yaml")
    ) as business_data:
        businesses = yaml.load(business_data)

    if any("publications" in item for item in data["order"]):
        if "publications" not in data:
            with open(
                os.path.join(config["YAML_DIR"],
                             config["YAML_PUBLICATIONS"] + ".yaml")
            ) as pub_data:
                pubs = yaml.load(pub_data)
            if pubs:
                data["publications"] = pubs
            else:
                for item in data["order"]:
                    if "publications" in item:
                        data["order"].remove(item)
                        break

    hashes = {f: md5_hash(f)
              for f in glob.iglob("{}/*.tex".format(config["BUILD_DIR"]))}

    for context in tqdm.tqdm((HTML_CONTEXT, LATEX_CONTEXT, MARKDOWN_CONTEXT),
                             leave=True, desc="Rendering résumé", unit="type"):
        process_resume(context, data)

    if businesses:
        for business in tqdm.tqdm(businesses,
                                  desc="Generating cover letters",
                                  unit="letter",
                                  leave=True):
            data["business"] = businesses[business]
            data["business"]["body"] = LATEX_CONTEXT.render_template(
                config["LETTER_FILE_NAME"], data
            )
            process_resume(LATEX_CONTEXT, data, base=business)

    compile_latex(data["engine"], hashes)
    copy_to_output()


def load_yaml(filename):
    with open(filename) as file:
        return yaml.load(file)


def process_resume(context, data, base=config["BASE_FILE_NAME"]):
    rendered_resume = context.render(data)
    context.write(rendered_resume, base=base)


def compile_latex(engine, hashes):
    files = [file for file in glob.iglob("{}/*.tex".format(config["BUILD_DIR"]))
             if (file in hashes and md5_hash(file) != hashes[file])
                 or not os.path.exists(file.replace(".tex", ".pdf"))
             ]
    if files:
        for file in tqdm.tqdm(files,
                              desc="Generating PDFs",
                              leave=True,
                              unit="pdf"):
            subprocess.call("{} -output-dir={} {}".format(engine,
                                                          config["BUILD_DIR"],
                                                          file).split())


def copy_to_output():
    for ext in ("pdf", "md", "html"):
        for file in glob.iglob("{}/*.{}".format(config["BUILD_DIR"], ext)):
            if os.path.basename(file).startswith("0_"):
                shutil.copyfile(file,
                                os.path.join(config["OUTPUT_DIR"],
                                             os.path.basename(file)[2:]))
            else:
                shutil.copy(file, os.path.join(config["OUTPUT_DIR"],
                                               config["LETTERS_DIR"]))


def md5_hash(filename):
    with open(filename) as fin:
        return hashlib.md5(fin.read().encode()).hexdigest()


class ContextRenderer(object):
    def __init__(self, context_name, filetype, jinja_options, replacements):
        self.filetype = filetype
        self.replacements = replacements

        context_templates_dir = os.path.join(config["TEMPLATES_DIR"],
                                             context_name)

        self.base_template = config["BASE_FILE_NAME"]
        self.context_name = context_name
        self.context_type_name = self.context_name + "type"

        self.jinja_options = jinja_options.copy()
        self.jinja_options["loader"] = jinja2.FileSystemLoader(
            searchpath=context_templates_dir
        )
        self.jinja_options["undefined"] = jinja2.StrictUndefined
        self.jinja_env = jinja2.Environment(**self.jinja_options)

        self.known_types = [os.path.splitext(os.path.basename(s))[0]
                            for s in glob.iglob(
                                os.path.join(context_templates_dir,
                                             config["SECTIONS_DIR"],
                                             "*{}".format(self.filetype)))]

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
        for (section_tag, show_title, section_title,
             section_type) in tqdm.tqdm(data["order"],
                                        desc=self.context_name,
                                        unit="sections",
                                        nested=True,
                                        leave=True):
            section_data = {"name": section_title} if show_title else {}
            section_content = data[section_tag]
            section_data["items"] = section_content
            section_data["theme"] = data["theme"]

            if section_type and section_type.startswith(self.context_type_name):
                section_type = section_type.split("_", maxsplit=1)[1]
            if not section_type and section_tag in self.known_types:
                section_type = section_tag
            if section_type not in self.known_types:
                section_type = config["DEFAULT_SECTION"]

            section_data["type"] = section_type

            if section_type == "double_items":
                section_data["items"] = self._make_double_list(
                    section_data["items"])

            section_template_name = os.path.join(config["SECTIONS_DIR"],
                                                 section_type)

            rendered_section = self.render_template(
                section_template_name, section_data)
            body += rendered_section.rstrip() + "\n\n\n"

        data["body"] = body
        data["updated"] = config["updated"]

        return self.render_template(self.base_template, data).rstrip() + "\n"

    def write(self, output_data, base=config["BASE_FILE_NAME"]):
        if base == config["BASE_FILE_NAME"]:
            prefix = "0_"
        else:
            prefix = ""
        output_file = os.path.join(config["BUILD_DIR"],
                                   "{prefix}{name}_{base}{ext}".format(
                                       prefix=prefix,
                                       name=self._name,
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
