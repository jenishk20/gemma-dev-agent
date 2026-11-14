Rails.application.routes.draw do
  get '/messages', to: 'messages#index'
  post '/messages', to: 'messages#create'
end