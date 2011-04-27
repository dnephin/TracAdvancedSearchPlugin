#!/bin/bash
# 
# TracSolrSearchPlugin - install.sh
# 
# Install and index solr
#

SOLR_VERSION="apache-solr-3.1.0"
SOLR_DIR=~/solr/



mkdir -p $SOLR_DIR || exit

# Download and extract solr
get http://www.ecoficial.com/apachemirror/lucene/solr/3.1.0/$SOLR_VERSION.tgz
tar -xf $SOLR_VERSION.tgz
mv $SOLR_VERSION $SOLR_DIR


pushd $SOLR_DIR/$SOLR_VERSION
