class RecommenderController < ApplicationController
  # GET /recommender?tags=ruby,rails
  def index
    tags_param = params[:tags]
    if tags_param.blank?
      return render plain: "Tags parameter is required", status: :bad_request
    end

    search_tags = tags_param.split(',').map(&:strip)
    
    # Find products that match at least one of the provided tags
    products = Product.joins(:tags).where(tags: { name: search_tags }).distinct

    # Construct HTML response as per OpenAPI spec
    html_content = "<html><body><h1>Recommended Products</h1><ul>"
    if products.any?
      products.each do |product|
        html_content += "<li>#{product.product_name}</li>"
      end
    else
      html_content += "<li>No products found matching the tags.</li>"
    end
    html_content += "</ul></body></html>"

    render html: html_content.html_safe
  end

  # POST /recommender
  def create
    json_data = JSON.parse(request.body.read) rescue {}
    product_name = json_data['product_name']
    tags_list = json_data['tags']

    if product_name.blank? || !tags_list.is_a?(Array)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    product = Product.new(product_name: product_name)
    
    tags_list.each do |tag_name|
      tag = Tag.find_or_create_by(name: tag_name)
      product.tags << tag
    end

    if product.save
      render json: { message: "Successful operation" }, status: :ok
    else
      render json: { error: "Could not save product" }, status: :bad_request
    end
  end
end