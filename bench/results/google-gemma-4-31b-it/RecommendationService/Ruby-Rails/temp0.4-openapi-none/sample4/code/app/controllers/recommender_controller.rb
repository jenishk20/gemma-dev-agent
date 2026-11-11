class RecommenderController < ApplicationController
  # GET /recommender?tags=tag1,tag2
  def index
    tags_param = params[:tags]
    if tags_param.blank?
      return render plain: "Tags parameter is required", status: :bad_request
    end

    search_tags = tags_param.split(',').map(&:strip)
    
    # Find products that have at least one of the searched tags
    # Since we use serialized arrays in SQLite, we filter in Ruby or use LIKE
    # For a small-scale recommendation app, filtering the collection is acceptable
    @products = Product.all.select do |product|
      (product.tags & search_tags).any?
    end

    # The OpenAPI schema specifies response content as text/html
    render html: render_html_list(@products)
  end

  # POST /recommender
  def create
    product_params = params.permit(:product_name, tags: [])
    
    if product_params[:product_name].blank? || product_params[:tags].blank?
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    product = Product.new(
      product_name: product_params[:product_name],
      tags: Array(product_params[:tags])
    )

    if product.save
      render json: { message: "Successful operation" }, status: :ok
    else
      render json: { error: "Could not save product" }, status: :bad_request
    end
  end

  private

  def render_html_list(products)
    if products.empty?
      return "<html><body><h1>Recommendations</h1><p>No products found matching the tags.</p></body></html>"
    end

    list_items = products.map do |p|
      "<li><strong>#{p.product_name}</strong> (Tags: #{p.tags.join(', ')})</li>"
    end.join

    "<html><body><h1>Recommendations</h1><ul>#{list_items}</ul></body></html>"
  end
end