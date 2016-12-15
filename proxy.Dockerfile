# Serves as proxy to 8 instances of ibrest, each with their own clientId
# Nginx handles SSL
FROM nginx:alpine
RUN apk add --update openssl
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/ibrest.key -out /etc/ssl/ibrest.crt -new -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com"
# Or copy your own serts
#COPY ./etc/ibrest.crt /etc/ssl/
#COPY ./etc/ibrest.key /etc/ssl/
COPY etc/nginx.conf /etc/nginx/nginx.conf

EXPOSE 443