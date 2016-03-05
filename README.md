About
-----
This repo contains the source I use to automatically generate [my résumé]
(http://github.com/masasin/resume) as a webpage and PDF from YAML input.

It was forked from [emichael/resume](https://github.com/emichael/resume),
which was in turn forked from [bamos/cv](https://github.com/bamos/cv).
I have added the ability to automatically generate PDFs with cover letters,
as well as have separate input files.

See the original repo for details about the choices of YAML, LaTeX, and Markdown.


How to run
----------
The dependencies are included in `requirements.txt` and can be installed using
`pip` with `pip install -r requirements.txt`. I recommend doing this inside a
`virtualenv`.

To run, call `generate.py`, which will look for YAML files in the input directory.


What to Modify
--------------
You can change any of the YAML files in the `inputs` directory. If you want
to change folders or file naming, change `config.yaml`. The image file in `img`,
should you be using one, also needs to change. Finally, take a look at the
`templates` directory to see if you want to edit anything.

Currently, you can `!include` different YAML files in `resume.yaml` to change
the order of the sections, but that might change in the future. `style.yaml`
defines the style of the résumé, and `publications.yaml` should contain all the
publications you want to show.

Finally, `businesses.yaml` should contain details about prospective employers.
A cover letter will be generated from `templates/latex/letter_body.tex`, and all
PDFs would be stored in the `outputs/cover_letters` directory, with each company
having its own name.

### Warnings
1. Strings in `resume.yaml` should be LaTeX (though, the actual LaTeX formatting
   should be in the left in the templates as much as possible).
2. If you do include any new LaTeX commands, make sure that one of the
   `REPLACEMENTS` in `generate.py` converts them properly.
3. The LaTeX templates use modified Jinja delimiters to avoid overlaps with
   normal LaTeX. See `generate.py` for details.
4. LaTeX files are only regenerated when the source changes or when the PDF
   does not exist.


License
-------
All of bamos's and emichael's original work is distributed under the MIT license
found in `LICENSE-bamos.mit` and `LICENSE-emichael.mit` respectively.

My modifications are distributed under the MIT license found in
`LICENSE-masasin.mit`.
