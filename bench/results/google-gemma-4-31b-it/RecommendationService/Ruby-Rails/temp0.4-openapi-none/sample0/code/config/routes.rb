Rails.application.routes.draw do
  match '/recommender', to: 'recommender#index', via: :get
  match '/recommender', to: 'recommender#create', via: :post
end