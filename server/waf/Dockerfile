FROM openresty/openresty:latest

LABEL maintainer="Blackpotbpanel WAF"
LABEL description="OpenResty WAF with GeoIP support"

USER root

# Install dependencies
RUN apt-get update && apt-get install -y \
    libmaxminddb-dev \
    libmaxminddb0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install lua-resty-maxminddb from GitHub
RUN cd /tmp && \
    git clone https://github.com/anjia0532/lua-resty-maxminddb.git && \
    cd lua-resty-maxminddb && \
    cp -r lib/resty /usr/local/openresty/lualib/ && \
    rm -rf /tmp/lua-resty-maxminddb

# Create necessary directories
RUN mkdir -p /usr/local/openresty/nginx/data \
    && mkdir -p /usr/local/openresty/nginx/logs \
    && mkdir -p /usr/local/openresty/nginx/rules \
    && mkdir -p /usr/local/openresty/nginx/lua \
    && mkdir -p /usr/local/openresty/nginx/waf_html

EXPOSE 80 443

CMD ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]
