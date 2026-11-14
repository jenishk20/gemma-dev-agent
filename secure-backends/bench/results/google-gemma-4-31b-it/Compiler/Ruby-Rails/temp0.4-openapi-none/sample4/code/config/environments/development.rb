require "concurrently"

module CompilationNow
  class Development < Rails::Application
    config.threshold = 0
    config.cache_store = :memory_store
    config.after_initialize do
      ActiveStorage.configuration.service = :test
    end
    config.force_ssl = false
  end
end