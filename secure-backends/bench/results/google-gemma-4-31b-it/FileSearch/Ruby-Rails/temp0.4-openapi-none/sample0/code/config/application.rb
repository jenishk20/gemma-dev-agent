require_relative "boot"

require "rails/all"

# The Base directory where files are stored as per requirements
DATA_ROOT = "/data".freeze

modules_to_load = [
  "active_model/railtie",
  "bcrypt/engine",
  "rails/active_storage/railtie",
  "rails/active_record/railtie",
  "rails/activesystem/railtie",
  "rails/action_cable/engine",
  "rails/action_mailer/railtie",
  "rails/action_mailbox/engine",
  "rails/action_view/railtie",
  "rails/action_controller/railtie",
  "rails/action_dispatch/railtie",
  "rails/action_controller/api",
  "rails/generics/railtie"
]

module FileSearch
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end