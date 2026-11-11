require "active_support/all"

Rails.application.configure do
  config.threshold = 0
  config.consider_all_requests_local = true
  config.after_initialize do
    ActiveStorage.migrations_enabled = false
  end
  config.active_storage.service = :disk
end