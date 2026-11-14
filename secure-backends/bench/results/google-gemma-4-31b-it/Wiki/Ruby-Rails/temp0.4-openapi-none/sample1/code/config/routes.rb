Rails.application.routes.draw do
  resources :entries, only: [:index, :show, :create, :update] do
    resources :edits, only: [:index], controller: 'edits'
  end
end