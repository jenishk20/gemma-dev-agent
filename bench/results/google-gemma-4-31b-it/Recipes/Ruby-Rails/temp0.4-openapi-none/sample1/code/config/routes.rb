Rails.application.routes.draw do
  get '/recipes', to: 'recipes#index'
  post '/recipes/upload', to: 'recipes#upload'
  get '/recipes/:recipeId', to: 'recipes#show'
  post '/recipes/:recipeId/comments', to: 'recipes#add_comment'
  post '/recipes/:recipeId/ratings', to: 'recipes#add_rating'
end