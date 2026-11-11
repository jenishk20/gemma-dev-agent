Rails.application.routes.draw do
  post '/upload', to: 'images#upload'
  get '/images/:imageId', to: 'images#show', constraints: { imageId: /[a-zA-Z0-9\-_]+/ }
end