Rails.application.routes.draw do
  get '/entries', to: 'entries#index'
  post '/entries', to: 'entries#create'
  get '/entries/:entryId', to: 'entries#show'
  put '/entries/:entryId', to: 'entries#update'
  get '/entries/:entryId/edits', to: 'entries#history'
end