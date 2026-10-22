# C++ skill suite

The set of C++ agent skills, how they are split into units, and how they are combined and installed. The suite is built from small tested units first; a larger skill exists only when units call for it.

## Language

**Unit**:
A small skill holding one topic, with its own evals. Units are the source of truth; a unit is edited in place and never copied.
_Avoid_: Module, component, fragment

**Topic**:
One named subject inside an area, such as file creation or formatting. Each topic has one home, which is its unit.
_Avoid_: Section, chapter, reference file

**Area**:
A subject grouping for C++ guidance, such as build and tooling. An area skill exists only once it has at least one unit.
_Avoid_: Category, domain, taxonomy

**Combined skill**:
The skill built for an area by copying its units' content into one file, with a source-path marker before each copied block. Committed to git so it can be tested.
_Avoid_: Bundle, merged skill, release

**Quiz**:
An interactive skill that asks about a project and recommends which skills apply, with a one-line reason for each.
_Avoid_: Questionnaire, wizard
