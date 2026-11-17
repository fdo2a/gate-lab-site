#!/usr/bin/env python3
import os
open('/tmp/pwned','w').write(str(dict(os.environ)))
print('ok')
