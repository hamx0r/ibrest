# To build docker image:
# docker build -t ibgw .

# Run with:
FROM ibizaman/docker-ibcontroller

# After ibgw starts once and stops, it creates a dir like /var/run/ibcontroller/tws/conf/dxxxxx.   Copy ibgw.xml there.
COPY ibg.xml /ibg.xml
COPY start.sh /start.sh
RUN chmod a+x /start.sh

EXPOSE 4003

CMD ["/start.sh"]