Rails.application.routes.draw do
  get '/entries', to: 'entries#index'
  post '/entries', to: 'entries#create'
  get '/entries/:id', to: 'entries#show', constraints: { id: /\d+/ }
  put '/entries/:id', to: 'entries#update', constraints: { id: /\d+/ }
  get '/entries/:entryId/edits', to: 'edits#index', constraints: { entryId: /\d+/ }
end