#!/bin/sh


CMD="python3 main.py"

if [ -n "${THESO_CONFIG}" ]; then
  CMD="$CMD --thesaurus-config ${THESO_CONFIG}"
fi

if [ -n "${GRAPH_CONFIG}" ]; then
  CMD="$CMD --graph_config ${GRAPH_CONFIG}"
fi

if [ -n "${DUMP_PATH}" ]; then
  CMD="$CMD --dump-path ${DUMP_PATH}"
fi

exec $CMD