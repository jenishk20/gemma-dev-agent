Rails.application.routes.draw do
  post '/upload', to: 'images#upload'
  get '/images/:imageId', to: 'images#show', as: :image
end