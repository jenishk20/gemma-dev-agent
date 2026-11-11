require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0
  config.api_only = true
  config.active_storage.service = :local
end