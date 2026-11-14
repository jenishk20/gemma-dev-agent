Rails.application.routes.draw do
  get '/entries', to: 'entries#index'
  post '/entries', to: 'entries#create'
  get '/entries/:id', to: 'entries#show'
  put '/entries/:id', to: 'entries#update'
  get '/entries/:id/edits', to: 'entries#edits'
end