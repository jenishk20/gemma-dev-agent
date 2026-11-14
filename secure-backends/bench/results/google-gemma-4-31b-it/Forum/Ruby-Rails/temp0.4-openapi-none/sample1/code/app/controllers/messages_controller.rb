class MessagesController < ApplicationController
  # GET /messages
  def index
    limit = params[:limit] || 10
    offset = params[:offset] || 0
    sort = params[:sort] || 'DESC'
    
    # Ensure sort is either ASC or DESC
    direction = sort.upcase == 'ASC' ? :asc : :desc
    
    @messages = Message.order(created_at: direction)
                      .limit(limit.to_i)
                      .offset(offset.to_i)

    # The OpenAPI spec requires text/html for the GET response
    render html: render_messages_html(@messages)
  end

  # POST /messages
  def create
    message = Message.new(message_params)
    if message.save
      render json: { status: 'Successful operation' }, status: :ok
    else
      render json: { errors: message.errors.full_messages }, status: :bad_request
    end
  end

  private

  def message_params
    params.require(:Message).permit(:content, :username) rescue params.permit(:content, :username)
    # The schema defines the body as a Message object. 
    # Rails usually expects params to be wrapped or flat depending on the client.
    # We handle both for robustness.
    if params[:Message].is_a?(Hash)
      params.require(:Message).permit(:content, :username)
    else
      params.permit(:content, :username)
    end
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