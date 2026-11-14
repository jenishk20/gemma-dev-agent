class MessagesController < ApplicationController
  # GET /messages
  def index
    limit = (params[:limit] || 10).to_i
    offset = (params[:offset] || 0).to_i
    sort_direction = (params[:sort] || 'desc').upcase == 'ASC' ? :asc : :desc

    @messages = Message.order(created_at: sort_direction)
                       .limit(limit)
                       .offset(offset)

    # The OpenAPI spec requires text/html response for the GET method
    render html: render_forum_page(@messages)
  end

  # POST /messages
  def create
    # The OpenAPI spec defines the request body as application/json
    message = Message.new(message_params)

    if message.save
      render json: { status: 'success' }, status: :ok
    else
      render json: { errors: message.errors.full_messages }, status: :bad_request
    end
  end

  private

  def message_params
    params.require(:Message).permit(:content, :username) rescue params.permit(:content, :username)
    # Handling both wrapped (Message: { ... }) and flat JSON inputs
    if params[:Message].is_a?(Hash)
      params.require(:Message).permit(:content, :username)
    else
      params.permit(:content, :username)
    end
  end

  def render_forum_page(messages)
    html = "<html><head><title>MyForum</title></head><body>"
    html += "<h1>MyForum Messages</h1>"
    html += "<form action='/messages' method='post' style='display:none;'> <!-- API expects JSON, but this is for visual context --> </form>"
    html += "<ul>"
    messages.each do |m|
      html += "<li><strong>#{m.username}</strong>: #{m.content} <small>(#{m.created_at})</small></li>"
    end
    html += "</ul>"
    html += "</body></html>"
    html
  end
end