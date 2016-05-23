FROM alpine

RUN echo -e '#!/bin/sh\nwc $1 > $2\n' > /bin/wca && chmod +x /bin/wca

ENTRYPOINT ["/bin/wca"]
CMD ["/input/input", "/output/output"]