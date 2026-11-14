Rails.application.routes.draw do
  post '/concatenate', to: 'pdf_concatenation#concatenate'
end