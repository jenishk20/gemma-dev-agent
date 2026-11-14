class ApplicationController < ActionController::API
  # Since the OpenAPI schema requests text/html for some endpoints, 
  # we include ActionView::Helpers to render simple HTML strings.
  include ActionView::Helpers::TagHelper
  include ActionView::Helpers::TextHelper
end