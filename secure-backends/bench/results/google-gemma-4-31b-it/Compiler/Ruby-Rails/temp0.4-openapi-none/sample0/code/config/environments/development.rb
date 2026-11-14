require "rails/all"

CompilationNow::Application.configure do
  config.threshold = 100
  config.consider_all_requests_local = true

  # Configure content type for JSON
  config.active_support.time_zone = "UTC"
  config.action_dispatch.time_zone = "UTC"
  config.time_zone = "UTC"
  config.action_mailer.default_url_options = { host: 'localhost', port: 3000 }
  config.action_cable.url = "ws://localhost:3000/cable"
  config.action_controller.allow_rescue = false
  config.active_storage.service = :local
end