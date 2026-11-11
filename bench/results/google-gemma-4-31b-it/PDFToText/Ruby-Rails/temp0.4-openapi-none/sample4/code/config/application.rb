require_relative "boot"

require "rails/all"

# The Requests API Application
module PdfToTextConverter
  module Application
    config.load_defaults 8.0
    config.api_only = true
  end
end