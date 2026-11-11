class ApplicationController < ActionController::API
  # Allow HTML responses even in API mode for the specific requirements of the schema
  def render_html(template_name, locals = {})
    render layout: false, template: template_name, locals: locals
  end
end