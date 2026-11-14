class MessagesController < ApplicationController
  def index
    limit = (params[:limit] || 10).to_i
    offset = (params[:offset] || 0).to_i
    sort = params[:sort]&.upcase == 'ASC' ? :asc : :desc

    @messages = Message.order(created_at: sort).limit(limit).offset(offset)

    # The OpenAPI spec requires text/html for the GET response
    render html: render_messages_html(@messages)
  end

  def create
    message = Message.new(message_params)
    if message.save
      render json: { status: 'Created' }, status: :ok
    else
      render json: { errors: message.errors.full_messages }, status: :bad_request
    end
  end

  private

  def message_params
    params.require(:Message).permit(:content, :username)
  end

  def render_messages_html(messages)
    html = "<html><body><h1>Forum Messages</h1><ul>"
    messages.each do |m|
      html += "<li><strong>#{m.username}</strong>: #{m.content} <small>(#{m.created_at})</small></li>"
    end
    html += "</ul></body></html>"
    html
  end
end