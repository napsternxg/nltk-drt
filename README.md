# nltk-drt
Automatically exported from code.google.com/p/nltk-drt


This is an extension of the Discourse Representation Theory (DRT) component of the Natural Language Toolkit (NLTK). A resolution component has been added to the basic DRT machinery: Following van der Sandt 1992, it handles both anaphora and presupposition resolution. Anaphora resolution builds on the ideas of Blackburn & Bos 1999, taking into account syntactic information, thematic roles and antecedent proximity. The presupposition resolution component improves on the algorithm due to van der Sandt by making use of ontology. An inference component checks the readings generated by the resolution component for admissibility. A temporal component adds a simple handling of temporal conditions. It borrows heavily from the work on tense and aspect by Kamp & Reyle 1993.


## License:
Apache License 2.0

## Original README

Copyright 2010 Alexander Kislev, Peter Makarov, Emma Li

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

==============
 Installation
==============

Before using this library you must have NLTK installed. Make sure that you also
install Prover9 2009-11A and download WordNet 3.0 data.
See NLTK documentation (http://www.nltk.org/).

Download the latest nltk-drt*.tar.gz file from
http://code.google.com/p/nltk-drt/downloads/.

Extract the archive, by typing into shell prompt:
tar xvfz nltk-drt*.tar.gz

Change directory:
cd nltk-drt/src/

==================
 Archive Contents
==================

./nltk-drt:
api/ data/ src/

./nltk-drt/api:
epydoc.config       -a configuration file to generate api documentation using
                     epydoc

./nltk-drt/data:
grammar.fcfg        -an example fcfg grammar used for testing purposes

./nltk-drt/src:
curt.py             -a script to run a dialog system based on grammar.fcfg
nltkfixtemporal.py  -fixes bug in DRT.draw() method in NLTK 2.0b9
temporaldrt.py      -extends presuppdrt.py with temporal semantics
util.py             -tokenization and testing glue code
wntemporaldrt.py    -extends temporaldrt.py with WordNet functionality
inference.py        -inference tools module
presuppdrt.py       -the basic functionality of Presupposition DRT
test.py             -the test suite from the paper

=======
 Usage
=======

The files in the nltk-drt/src/ directory constitute a library that could be
used as a drop-in replacement for the in-built drt.py module from the NLTK
project. The functionality of the modules is described in the code as well
as in the NLTK-DRT.pdf file. Additionally it has two test programs which
could be run from a command line to make sure that all the required software
is running properly.

To run the general test suite, as described in the test suite section of the
attached NLTK-DRT.pdf file, use:
python test.py

In case the test has been passed, all the required modules are present and the
library is fully functional.

To run curt with the supplied grammar, located at nltk-drt/data/grammar.fcfg,
use:
python curt.py

Enjoy!



