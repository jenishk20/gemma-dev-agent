Rails.application.routes.draw do
  post 'heartbeat', to: 'monitoring#heartbeat'
  post 'services', to: 'monitoring#services'
end