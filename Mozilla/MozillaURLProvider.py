#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson, 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import re
import urllib2
import xml.etree.ElementTree as ET

from autopkglib import Processor, ProcessorError
from urllib import quote

__all__ = ["MozillaURLProvider"]


MOZ_BASE_URL = "http://download-origin.cdn.mozilla.net"
S3_XMLNS = "http://s3.amazonaws.com/doc/2006-03-01/"


class MozillaURLProvider(Processor):
    description = "Provides URL to the latest Firefox release."
    input_variables = {
        "product_name": {
            "required": True,
            "description": 
                "Product to fetch URL for. One of 'firefox', 'thunderbird'.",
        },
        "release": {
            "required": False,
            "description": ("Which release to download. Examples: 'latest', "
                "'latest-10.0esr', 'latest-esr', 'latest-beta'."),
        },
        "locale": {
            "required": False,
            "description": 
                    "Which localization to download, default is 'en_US'.",
        },
        "base_url": {
            "required": False,
            "description": "Default is '%s." % MOZ_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Mozilla product release.",
        },
    }
    
    __doc__ = description


    def ns_tag(self, tagname):
        """Helper function to format a tag as '{namespace}tagname'"""
        return "{%s}%s" % (S3_XMLNS, tagname)

    
    def get_mozilla_dmg_url(self, base_url, product_name, release, locale):
        """Return a download URL for a release by getting and parsing
        the AWS S3 Bucket XML using a given prefix, assembled from
        'product_name', 'release', 'locale'."""

        # Allow locale as both en-US and en_US.
        locale = locale.replace("_", "-")
        
        # Construct download directory URL.
        release_dir = release.lower()
        
        # Build the query string for the S3 Bucket
        query_string = "prefix=pub/%s/releases/%s/mac/%s" % (
            product_name, release_dir, locale)
        bucket_url = "%s/?%s" % (base_url, query_string)

        # Read S3 Bucket XML
        try:
            f = urllib2.urlopen(bucket_url)
            xml = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (bucket_url, e))

        root = ET.fromstring(xml)
        contents = root.findall(self.ns_tag("Contents"))
        if not contents:
            raise ProcessorError("Expected a 'Contents' element from S3 Bucket XML, but none found.")

        # The 'Key' key is actually a relative URL to a file download
        urls = [key.find(self.ns_tag("Key")).text for key in list(contents)]
        if len(urls) > 1:
            self.output("Got multiple URLs: %s" % ", ".join(urls))
            raise ProcessorError("Got multiple 'Contents' elements. We should have only one.")

        url = "%s/%s" % (MOZ_BASE_URL, urls[0])
        # Percent-quote the path to handle spaces
        safe_url = quote(url, safe=":/")

        return safe_url

    
    def main(self):
        # Determine product_name, release, locale, and base_url.
        product_name = self.env["product_name"]
        release = self.env.get("release", "latest")
        locale = self.env.get("locale", "en_US")
        base_url = self.env.get("base_url", MOZ_BASE_URL)
        
        self.env["url"] = self.get_mozilla_dmg_url(
                                        base_url, product_name, release, locale)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == "__main__":
    processor = MozillaURLProvider()
    processor.execute_shell()
    
