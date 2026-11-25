#blog/views
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, UserEditForm
from .models import Category, Post, Comment

from django.views.generic import TemplateView

User = get_user_model()
POSTS_PER_PAGE = 10


def get_posts(queryset=Post.objects.all(), only_published=True):
    queryset = queryset.select_related(
        'category', 'location', 'author'
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    if only_published:
        queryset = queryset.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
    return queryset


def paginate(request, queryset):
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get('page'))


def index(request):
    page_obj = paginate(request, get_posts())
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(get_posts(), pk=post_id)
    context = {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    page_obj = paginate(
        request, get_posts(Post.objects.filter(category=category))
    )
    return render(
        request,
        'blog/category.html',
        {'category': category, 'page_obj': page_obj},
    )


def profile(request, username):
    profile = get_object_or_404(User, username=username)
    posts = get_posts(
        Post.objects.filter(author=profile),
        only_published=request.user != profile,
    )
    context = {'profile': profile, 'page_obj': paginate(request, posts)}
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    form = UserEditForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    instance = get_object_or_404(Post, pk=post_id)
    form = PostForm(request.POST or None, instance=instance)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    context = {'form': form}
    if form.is_valid():
        form.save()
    return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, post_id):
    instance = get_object_or_404(Post, pk=post_id)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(instance=instance)
    context = {'form': form}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        # Создаём объект поздравления, но не сохраняем его в БД.
        words = form.save(commit=False)
        # В поле author передаём объект автора поздравления.
        words.author = request.user
        # В поле birthday передаём объект дня рождения.
        words.post = post
        # Сохраняем объект в БД.
        words.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    instance = get_object_or_404(Comment, pk=comment_id, post=post)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    context = {'comment': instance}
    if request.method == 'POST':
        instance.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', context)


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    instance = get_object_or_404(Comment, pk=comment_id, post=post)
    if instance.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=instance)
    context = {'form': form, 'comment': instance}
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', context)
