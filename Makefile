#!/usr/bin/env make

# MAKE FILE FOR ALL THE THINGS
#
# set sw=4

default: all

CURRENT_TEAM := oke

PATCHING := "FALSE"
PKG_MGR := "apt"

# Not working...
# ... WORKING_DIR := "$(pwd)"
#
#
#

# Lexicography

# SYMBOLS
#
# LEXER
#
#

# PATH := "PATH"

# CI_PLATFORM_NAMES := "${bitbucket:~gitlab}"

GO_ROOT := ${HOME}/go

COMPANY_GO_ROOT := ${GOPATH}/src/${company_tld}

DIGITS := 0 1 2 3 4 5 6 7 8 9

IDX := 0

CPUS := 0 1

# CONST
## HOME := "${HOME}"
AWAY := "${AWAY:-AWAY}"

# CONSTANT
OPERATOR_NAME := "Andrew Pryde"

REGISTERS := IDX

# PATHS
#
BASE_PATH := "$(HOME)/.dotfiles"

# HTTP -> BEGETS
VERBS := GET | POST | PUT | HEAD

# PER LANG OPS
PY_OP := MAKE_PYTHON_VENV

# VERSIONS
PYTHON_VERSION := 3

# TOOL URLS

JIRA_INSTANCE := $("env | grep -i "^jira_*$")

DB_NAME := "${SOURCE_DB}"

LANGS := PYTHON | PYTHON_2 | PYTHON_3

## VARS
STORE_NAME := $(env | grep -i (${DB_NAME}))

LOCAL_BIN_PATH := ${HOME}/.local/bin

TASK_L :=  { }

# SQL STORED_PROCEDURES

# VALUE := LOOKUP(${DATA_SOURCE})

# PARSING
#
#
#

.PHONY:
build:
	go build "./cmd/*" -C ${COMPANY_GO_ROOT}/${UNAME}/${CURRENT_TEAM}-tools/cmd/*  -o $(basename ${LOCAL_BIN_PATH})
	source "${GOPATH}/src/bitbucket.${company_tld}/$(whoami)/${CURRENT_TEAM}-tools/env.sh"

.PHONY:
up:
<<<<<<< HEAD
	@echo "Bringing up ${OPERATOR_NAME}'s System"
	@env RCRC=${HOME}/.dotfiles/rcrc rcup
=======
	env RCRC=${HOME}/.dotfiles/rcrc rcup
>>>>>>> b58458be (Checkpoint)

.PHONY:
build: up

mkvirtualenv:
	python${PYTHON_VERSION} -m venv ${BASE_PATH}/python3

.PHONY:
all: build test install

.PHONY:
install: build
	# COPY TO BIN
	mkdir -p ${HOME}/.local/bin/

.PHONY:
clean:
	@rm -rf ${HOME}/.local/bin/

.PHONY:
clean-house: # BEGETS
	@rm -rf ${HOME}/.dotfiles/.git/
	@rm -rf ${HOME}/.local/bin/

# ```
# F(PYTHON_VERSION):
# -> PIP_PATH := "${HOME}/.dotfiles/python${PYTHON_VERSION}/bin/pip"
# ```` | pbcopy

# PIP_X := $("$(${HOME})/.dotfiles/python$({PYTHON_VERSION}"))
PY_BODY_FUNC_NAME := "__main__"

# PARSER

ABRS := JQL | OSQL  | SQL | PY2 | PY3
LANG_NAME := "JQL | ORACLE_SQL | SQL"
SYMBOLS := { E PIC S}
TERMS := SET VAR LEXER FUNC
SYMBOLS := SET {A..Z a..z 0-9]

## Types
DO_WORK_FUNC_TYPE := F (OBJECT) -> OBJECT
CLASS_T := "Property<T>"

## FUNCS

PUBLISH_EPIC := F(DO_WORK)
REDUCE_F := F(W) -> x -> $


.PHONY:
python:
	PIP_X := "$(${BASE_PATH})/python$(${PYTHON_VERSION})"
	$(python -m venv "${PIP_X}")

.PHONY:
test:
	# WRITE TESTS... and then run them...?
	@/usr/bin/env python -m test.py ./

.PHONY:
patching:
	@echo "Patching $(hostname)..."
	@sudo ${PKG_MGR} update
	@sudo ${PKG_MGR} upgrade -y
	@sudo ${PKG_MGR} autoremove
	@sudo shutdown -r now
