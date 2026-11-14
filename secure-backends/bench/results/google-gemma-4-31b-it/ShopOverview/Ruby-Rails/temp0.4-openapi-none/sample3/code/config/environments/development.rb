require "active_support/core_ext/integer/time"

module MerchantWebApp
  class Development < Rails::Application
    config.threshold = 500
    config.cache_store = :memory_store
    config.log_level = :debug

    # Disable assets pipeline as requested
    config.public_file_server.enabled = true
  end
end