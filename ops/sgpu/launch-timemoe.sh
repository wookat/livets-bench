#!/bin/bash
exec bash ops/sgpu/launch-common.sh timemoe time-moe-50m "transformers==4.40.1 accelerate torch"
