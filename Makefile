#!/usr/bin/env make

# MAKE FILE FOR ALL THE THINGS
#
# vim: set ft=make sw=4:

default: all

UNAME := apryde
HOSTNAME := $$(hostname)

GO_ROOT := ${HOME}/go

SRC_CONTROL_PLATFORM := bitbucket
COMPANY_GO_ROOT ?= ${GO_ROOT}/src/${SRC_CONTROL_PLATFORM}.${OCI_INTERNAL_TLD}
CURRENT_TEAM ?= oke

# CONSTANT
OPERATOR_NAME ?= "Andrew Pryde"


# PATHS
#
BASE_PATH := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# VERSIONS
PYTHON_VERSION := 3

# TOOL URLS

JIRA_INSTANCE := $("env | grep -i "^jira_*$")

## VARS

DB_NAME := "${SOURCE_DB}"
STORE_NAME := $(env | grep -i (${DB_NAME}))
TASK_L :=  { }

# SQL STORED_PROCEDURES

# VALUE := LOOKUP(${DATA_SOURCE})

RCRC := "$${HOME}/.dotfiles/rcrc"
.PHONY:
up:
	@echo "Bringing up ${OPERATOR_NAME}'s System"
	@env RCRC="$${HOME}/.dotfiles/rcrc" rcup

.PHONY:
mkvirtualenv:
	python${PYTHON_VERSION} -m venv ${BASE_PATH}/venv
	${BASE_PATH}/venv/bin/pip install -r requirements.txt

.PHONY:
all: up

.PHONY:
clean:
	@rm -rf ${HOME}/.local/bin/

.PHONY:
clean-house: # BEGETS CLEAN MIND
	@rm -rf ${HOME}/.dotfiles/.git/
	@rm -rf ${HOME}/.local/bin/
	@rm -rf /etc/NetworkManager/system-connections/*.nmconnection


.PHONY:
python:
	PIP_X := "$(${BASE_PATH})/python$(${PYTHON_VERSION})"
	$(python -m venv "${PIP_X}")

.PHONY:
test:
	# WRITE TESTS... and then run them...?
	@/usr/bin/env python -m test.py ./

GET_KERNAL_VERSION := $$(uname -r)

.PHONY:
sys-info:
	@echo ""
	@echo "System Info"
	@echo "-----------"
	@echo "Comapny: Oracle (OCI)"
	@echo ""
	@echo Owner: $(OPERATOR_NAME)
	@echo ""
	@echo "Routes: "
	@echo ""
	@ip route show
	@echo ""
	@echo ""
	@echo "Network Details"
	@echo "-----------"
	@echo ""
	@echo "Host Name: ${HOSTNAME}"
	@echo ""
	@echo "Interfaces:"
	@echo ""
	@ip address show lo
	@echo ""
	@echo "Kernal: " ${GET_KERNAL_VERSION}
	@echo ""
	@echo "Installed Kernal Packages: "
	@dpkg --list 'linux-image*' | grep ^ii | cut -d' ' -f3 | grep -v ${GET_KERNAL_VERSION}
	@echo ""
	@echo "Boot Parition Space:"
	@df /boot/ -h
	@echo ""

PKG_MGR := "apt" # TODO(apryde): yum

.PHONY:
patching: sys-info
	@echo "Patching $(${HOSTNAME})..."
	@echo ""

	@${PKG_MGR} update -y
	@${PKG_MGR} upgrade -y
	@${PKG_MGR} autoremove -y

	@update-grub
	# TODO(apryde): previous kernal not current!
	# @apt-get remove ${GET_KERNAL_VERSION}
	@shutdown -r now

.PHONY:
ol-migration:
	# TODO(apryde):
	#  - Kernal
	#  - Package name translation
	#  - Testing

# Jira Ticket Handler
#####################

# This is garbage... one day maybe.

# SYMBOLS
#########

DIGITS := 0 1 2 3 4 5 6 7 8 9

IDX := 0

CPUS := 0 1

REGISTERS := IDX



# LEXER
#######

# PARSER
########

ABRS := JQL | OSQL | SQL | PY2 | PY3
LANG_NAME := JQL | ORACLE_SQL | SQL
SYMBOLS := { E PIC S}
TERMS := SET VAR LEXER FUNC
SYMBOLS := SET {A..Z a..z 0-9]

## Types
DO_WORK_FUNC_TYPE := F (OBJECT) -> OBJECT
CLASS_T := "Property<T>"

## FUNCS

PUBLISH_EPIC := F(DO_WORK)
REDUCE_F := F(W) -> x -> $
