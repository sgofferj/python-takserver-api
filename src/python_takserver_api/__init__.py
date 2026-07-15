#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# takserver.py from https://github.com/sgofferj/takserver-api-python
#
# Copyright Stefan Gofferje
#
# Licensed under the Gnu General Public License Version 3 or higher (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.gnu.org/licenses/gpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Python module for talking to a (tak.gov) tak server"""

from __future__ import annotations
from .tak_class import Server
from .tak_mission_api import build_mission_package

__all__ = ["Server", "build_mission_package"]
__version__ = "0.1.0"  # NOTE Use `bump2version --config-file patch` to bump versions correctly
