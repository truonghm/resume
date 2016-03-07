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


with open("config.yaml") as config_file:
    CONFIG = yaml.load(config_file)


def load_yaml(filename):
    with open(filename) as file:
        return yaml.load(file)


def files_of_type(ext, directory="."):
    yield from glob.iglob("{}/*{}".format(directory, ext))


def environment_setup():
    os.makedirs(CONFIG["BUILD_DIR"], exist_ok=True)
    os.makedirs(os.path.join(CONFIG["OUTPUT_DIR"], CONFIG["LETTERS_DIR"]),
                exist_ok=True)


def md5(filename):
    with open(filename) as fin:
        return hashlib.md5(fin.read().encode()).hexdigest()


def hash_map(ext=".tex"):
    return {f: md5(f) for f in files_of_type(ext, CONFIG["BUILD_DIR"])}


class ResumeGenerator(object):
    def __init__(self):
        self.data = load_yaml(os.path.join(CONFIG["YAML_DIR"],
                                           CONFIG["YAML_MAIN"] + ".yaml"))
        self.starting_hashes = hash_map()

    def run(self, contexts):
        self.handle_publications()
        self.generate_resumes(contexts)

        if LATEX_CONTEXT in contexts:
            self.generate_cover_letters()
            self.compile_latex()

        self.copy_to_output_dir(contexts)

    def handle_publications(self):
        if not any("publications" in item for item in self.data["order"]):
            return

        if "publications" not in self.data:
            pubs = load_yaml(
                os.path.join(CONFIG["YAML_DIR"],
                             CONFIG["YAML_PUBLICATIONS"] + ".yaml"))
            if pubs:
                self.data["publications"] = pubs
            else:
                for item in self.data["order"]:
                    if "publications" in item:
                        self.data["order"].remove(item)
                        break

    def process_resume(self, context, base=CONFIG["BASE_FILE_NAME"]):
        rendered_resume = context.render_resume(self.data)
        context.write(rendered_resume, base=base)

    def generate_resumes(self, contexts):
        for context in tqdm.tqdm(contexts, leave=True, desc="Rendering résumé",
                                 unit="formats"):
            self.process_resume(context)

    def generate_cover_letters(self):
        businesses = load_yaml(
            os.path.join(CONFIG["YAML_DIR"],
                         CONFIG["YAML_BUSINESSES"] + ".yaml"))

        if not businesses:
            return

        for business in tqdm.tqdm(businesses, desc="Generating cover letters",
                                  unit="letter", leave=True):
            self.data["business"] = businesses[business]
            self.data["business"]["body"] = LATEX_CONTEXT._render_template(
                CONFIG["LETTER_FILE_NAME"], self.data
            )
            self.process_resume(LATEX_CONTEXT, base=business)

    def compile_latex(self):
        changed_files = [file
                         for file in files_of_type(".tex", CONFIG["BUILD_DIR"])
                         if ((file in self.starting_hashes
                              and md5(file) != self.starting_hashes[file])
                             or not os.path.exists(file.replace(".tex",
                                                                ".pdf")))]
        if not changed_files:
            return

        for file in tqdm.tqdm(changed_files, desc="Generating PDFs",
                              leave=True, unit="pdf"):
            subprocess.call("{} -output-dir={} {}".format(self.data["engine"],
                                                          CONFIG["BUILD_DIR"],
                                                          file).split())

    @staticmethod
    def copy_to_output_dir(contexts):
        for context in contexts:
            for file in files_of_type(context.filetype, CONFIG["BUILD_DIR"]):
                if os.path.basename(file).startswith("0_"):
                    shutil.copyfile(file,
                                    os.path.join(CONFIG["OUTPUT_DIR"],
                                                 os.path.basename(file)[2:]))
                else:
                    shutil.copy(file, os.path.join(CONFIG["OUTPUT_DIR"],
                                                   CONFIG["LETTERS_DIR"]))


class ContextRenderer(object):
    def __init__(self, *, context_name, filetype, jinja_options, replacements):
        self.base_template = CONFIG["BASE_FILE_NAME"]
        self.context_name = context_name

        self.filetype = filetype
        self.replacements = replacements

        context_templates_dir = os.path.join(CONFIG["TEMPLATES_DIR"],
                                             context_name)

        jinja_options = jinja_options.copy()
        jinja_options["loader"] = jinja2.FileSystemLoader(
            searchpath=context_templates_dir
        )
        jinja_options["undefined"] = jinja2.StrictUndefined
        self.jinja_env = jinja2.Environment(**jinja_options)

        self.known_section_types = [os.path.splitext(os.path.basename(s))[0]
                                    for s in files_of_type(
                                        self.filetype,
                                        os.path.join(context_templates_dir,
                                                     CONFIG["SECTIONS_DIR"]))]

    def _make_replacements(self, data):
        data = copy.copy(data)

        if isinstance(data, str):
            for o, r in self.replacements.items():
                data = re.sub(o, r, data)

        elif isinstance(data, dict):
            for k, v in data.items():
                data[k] = self._make_replacements(v)

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                data[idx] = self._make_replacements(item)

        return data

    @staticmethod
    def _make_double_list(items):
        double_list = [{"first": items[i * 2], "second": items[i * 2 + 1]}
                       for i in range(len(items) // 2)]
        if len(items) % 2:
            double_list.append({"first": items[-1]})
        return double_list

    def _render_template(self, template_name, data):
        return self.jinja_env.get_template(template_name + self.filetype)\
                             .render(**data)

    def _render_section(self, data, section):
        section_tag, show_title, section_title, section_type = section
        section_data = {"name": section_title} if show_title else {}
        section_data["items"] = data[section_tag]
        section_data["theme"] = data["theme"]

        section_type = self._find_section_type(section_tag, section_type)
        section_data["type"] = section_type

        if section_type == "double_items":
            section_data["items"] = self._make_double_list(
                section_data["items"])

        section_template_name = os.path.join(CONFIG["SECTIONS_DIR"],
                                             section_type)

        rendered_section = self._render_template(section_template_name,
                                                 section_data)
        return rendered_section

    def _find_section_type(self, section_tag, section_type):
        context_type_name = self.context_name + "type"
        if isinstance(section_type, list):
            for t in section_type:
                if t.startswith(context_type_name):
                    section_type = t
                    break
            else:
                section_type = section_type[0]

        if section_type and section_type.startswith(context_type_name):
            section_type = section_type.split("_", maxsplit=1)[1]
        if not section_type and section_tag in self.known_section_types:
            section_type = section_tag
        if section_type not in self.known_section_types:
            section_type = CONFIG["DEFAULT_SECTION"]

        return section_type

    # noinspection PyTypeChecker
    def render_resume(self, data):
        data = self._make_replacements(data)
        self.username = data["name"]["abbrev"]

        body = ""
        for section in tqdm.tqdm(data["order"], desc=self.context_name,
                                 unit="sections", nested=True, leave=True):
            body += self._render_section(data, section).rstrip() + "\n\n\n"
        data["body"] = body

        last_updated = time.localtime(git.Repo().head.commit.committed_date)
        data["updated"] = time.strftime(CONFIG["DATE_FMT"], last_updated)

        return self._render_template(self.base_template, data).rstrip() + "\n"

    def write(self, output_data, base=CONFIG["BASE_FILE_NAME"]):
        if base == CONFIG["BASE_FILE_NAME"]:
            prefix = "0_"
        else:
            prefix = ""
        output_file = os.path.join(CONFIG["BUILD_DIR"],
                                   "{prefix}{name}_{base}{ext}".format(
                                       prefix=prefix,
                                       name=self.username,
                                       base=base,
                                       ext=self.filetype)
                                   )
        with open(output_file, "w") as fout:
            fout.write(output_data)


LATEX_CONTEXT = ContextRenderer(
    context_name="latex",
    filetype=".tex",
    jinja_options=dict(
        block_start_string='~<',
        block_end_string='>~',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
        trim_blocks=True,
        lstrip_blocks=True,
    ),
    replacements={}
)


MARKDOWN_CONTEXT = ContextRenderer(
    context_name='markdown',
    filetype='.md',
    jinja_options=dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    replacements={
        r'\\ ': ' ',                      # spaces
        r'\\textbf{([^}]*)}': r'**\1**',  # bold text
        r'\\textit{([^}]*)}': r'*\1*',    # italic text
        r'\\LaTeX': 'LaTeX',              # \LaTeX
        r'\\TeX': 'TeX',                  # \TeX
        '---': '-',                       # em dash
        '--': '-',                        # en dash
        r'``([^\']*)\'\'': r'"\1"',       # quotes
    }
)


HTML_CONTEXT = ContextRenderer(
    context_name='html',
    filetype='.html',
    jinja_options=dict(
        trim_blocks=True,
        lstrip_blocks=True
    ),
    replacements={
        r'\\ ': '&nbsp;',                              # spaces
        r'\\textbf{([^}]*)}': r'<strong>\1</strong>',  # bold
        r'\\textit{([^}]*)}': r'<em>\1</em>',          # italic
        r'\\LaTeX': 'LaTeX',                           # \LaTeX
        r'\\TeX': 'TeX',                               # \TeX
        '---': '&mdash;',                              # em dash
        '--': '&ndash;',                               # en dash
        r'``([^\']*)\'\'': r'"\1"',                    # quotes
    }
)


def main():
    environment_setup()
    ResumeGenerator().run(contexts=(HTML_CONTEXT,
                                    LATEX_CONTEXT,
                                    MARKDOWN_CONTEXT))


if __name__ == '__main__':
    main()
