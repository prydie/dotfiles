#!/usr/bin/env make

# MAKE FILE FOR ALL THE THINGS
#
# vim: set ft=make sw=4:

SHELL := /bin/bash

default: all

# PATHS
#
BASE_PATH := $(HOME)/.dotfiles
RCRC ?= ${BASE_PATH}/rcrc

CURRENT_TEAM ?= CKS
GUID ?= apryde

COMPANY_INTERNAL_TLD ?= oraclecorp.com

# Package Management
####################

UNAME := $$(whoami)
HOSTNAME := $$(hostname)
PKG_MGR ?= apt # -> yum


# Go
####
GO_ROOT ?= ${HOME}/go
GO_PATH ?= ${HOME}/go

SRC_CONTROL_PLATFORM := bitbucket
COMPANY_GO_ROOT ?= ${GOPATH}/src/${SRC_CONTROL_PLATFORM}.oci.${COMPANY_INTERNAL_TLD}

# CONSTANTS
OPERATOR_NAME ?= "Andrew Pryde"

.PHONY:
build:
	@mkdir -p $(basename ${LOCAL_BIN_PATH})

.PHONY:
up: mkvirtualenv
	@echo "Bringing up ${OPERATOR_NAME}'s System"
	@bash  rcup

.PHONY:
mkvirtualenv:
	python3 -m venv ${BASE_PATH}/venv
	${BASE_PATH}/venv/bin/pip install -r requirements.txt

.PHONY:
all: build test

.PHONY:
install: build
	mkdir -p ${HOME}/.local/bin/
	@env RCRC=${HOME}/.dotfiles/rcrc rcup

.PHONY:
clean:
	@rm -rf ${HOME}/.local/bin/

.PHONY:
clean-house: # BEGETS CLEAN MIND
	@rm -rf ${HOME}/.dotfiles/.git/
	@rm -rf ${HOME}/.local/bin/
	@rm -rf ${HOME}/.local/bin/
	@rm -rf /etc/NetworkManager/system-connections/*.nmconnection

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
	@ip r show
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

.PHONY:
patching: sys-info
	@echo "Patching $(${HOSTNAME})..."
	@echo ""

	${PKG_MGR} update -y 2>&1 | tee /tmp/update.log
	${PKG_MGR} upgrade -y 2>&1 | tee /tmp/update.log
	${PKG_MGR} autoremove -y 2>&1 | tee /tmp/update.log
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


# Revision
##########

# SYMBOLS

# LEXER
#

# HTTP -> BEGETS
VERBS := GET | POST | PUT | HEAD

# PER LANG OPS
PY_OP := MAKE_PYTHON_VENV

DIGITS := 0 1 2 3 4 5 6 7 8 9

REGISTERS := IDX

IDX := 0
CPUS := 0 1

JIRA_INSTANCE := $("env | grep -i "^jira_*$")

DB_NAME := "${SOURCE_DB}"

## VARS
STORE_NAME := $(env | grep -i (${DB_NAME}))

LOCAL_BIN_PATH := ${HOME}/.local/bin

TASK_L :=  { }

# SQL STORED_PROCEDURES

# VALUE := LOOKUP(${DATA_SOURCE})

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
