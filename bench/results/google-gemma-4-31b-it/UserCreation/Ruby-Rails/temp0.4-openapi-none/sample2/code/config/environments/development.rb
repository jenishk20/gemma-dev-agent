require "rails/all"

Module InviteAPI
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.cache_store = :memory_cache
    config.log_level = :debug
  end
end